import argparse
import numpy as np
import pathlib
import pandas as pd
import torch
import torch.nn.functional as F
import wandb
import yaml

from dataloader import CustomDataset
from datetime import datetime
from torch import cuda
from torch.utils.data import DataLoader, RandomSampler, SequentialSampler
from torch.optim.lr_scheduler import ExponentialLR
from transformers import T5Tokenizer, T5ForConditionalGeneration


device = "cuda" if cuda.is_available() else "cpu"


def train(epoch, tokenizer, model, device, loader, optimizer, scheduler):
    model.train()
    for _, data in enumerate(loader, 0):
        y = data["target_ids"].to(device, dtype=torch.long)
        y_ids = y[:, :-1].contiguous()
        lm_labels = y[:, 1:].clone().detach()
        lm_labels[y[:, 1:] == tokenizer.pad_token_id] = -100
        ids = data["source_ids"].to(device, dtype=torch.long)
        mask = data["source_mask"].to(device, dtype=torch.long)

        outputs = model(
            input_ids=ids,
            attention_mask=mask,
            decoder_input_ids=y_ids,
            labels=lm_labels,
        )
        loss = outputs[0]

        if _ % 10 == 0 and args.wandb:
            wandb.log({"Training Loss": loss.item()})

        if _ % 500 == 0:
            print(f"Epoch: {epoch}, Loss:  {loss.item()}")

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()


def validate(epoch, tokenizer, model, device, loader):
    model.eval()
    predictions = []
    actuals = []
    with torch.no_grad():
        for _, data in enumerate(loader, 0):
            y = data["target_ids"].to(device, dtype=torch.long)
            ids = data["source_ids"].to(device, dtype=torch.long)
            mask = data["source_mask"].to(device, dtype=torch.long)

            generated_ids = model.generate(
                input_ids=ids,
                attention_mask=mask,
                max_length=25,
                min_length=4,
                do_sample=True,
                num_beams=4,
                top_k=20,
                temperature=0.75,
                no_repeat_ngram_size=2,
                repetition_penalty=1.25,
            )

            preds = [
                tokenizer.decode(
                    g, skip_special_tokens=True, clean_up_tokenization_spaces=True
                )
                for g in generated_ids
            ]
            target = [
                tokenizer.decode(
                    t, skip_special_tokens=True, clean_up_tokenization_spaces=True
                )
                for t in y
            ]
            if _ % 100 == 0:
                print(f"Completed {_}")

            predictions.extend(preds)
            actuals.extend(target)
    return predictions, actuals


def main(config):
    if args.wandb:
        wandb.init(project="", entity="")

    torch.manual_seed(*config["seed"].values())
    np.random.seed(*config["seed"].values())
    torch.backends.cudnn.deterministic = True

    tokenizer = T5Tokenizer.from_pretrained("t5-base", model_max_length=512)

    df = pd.read_csv(args.data_path, encoding="latin-1")
    df = df[["Premises", "Claim"]]
    df.Premises = "summarize: " + df.Premises
    print(df.head())

    train_size = 0.8
    train_dataset = df.sample(frac=train_size, random_state=config["seed"]["value"])
    val_dataset = df.drop(train_dataset.index).reset_index(drop=True)
    train_dataset = train_dataset.reset_index(drop=True)

    print("FULL Dataset: {}".format(df.shape))
    print("TRAIN Dataset: {}".format(train_dataset.shape))
    print("TEST Dataset: {}".format(val_dataset.shape))

    training_set = CustomDataset(
        train_dataset,
        tokenizer,
        *config["max_len"].values(),
        *config["conclusion_len"].values(),
    )
    val_set = CustomDataset(
        val_dataset,
        tokenizer,
        *config["max_len"].values(),
        *config["conclusion_len"].values(),
    )

    train_params = {
        "batch_size": config["train_batch_size"]["value"],
        "shuffle": True,
        "num_workers": 0,
    }

    val_params = {
        "batch_size": config["valid_batch_size"]["value"],
        "shuffle": False,
        "num_workers": 0,
    }

    training_loader = DataLoader(training_set, **train_params)
    val_loader = DataLoader(val_set, **val_params)

    model = T5ForConditionalGeneration.from_pretrained("t5-base")
    model = model.to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"]["value"]
    )
    scheduler = ExponentialLR(optimizer, gamma=config["gamma"]["value"])

    if args.wandb:
        wandb.watch(model, log="all")
    print("Initiating Fine-Tuning for the model on our dataset")

    for epoch in range(*config["train_epochs"].values()):
        train(epoch, tokenizer, model, device, training_loader, optimizer, scheduler)

    print(
        "Now generating consclusions on our fine tuned model for the validation dataset and saving it in a dataframe"
    )
    for epoch in range(*config["valid_epochs"].values()):
        predictions, actuals = validate(epoch, tokenizer, model, device, val_loader)
        final_df = pd.DataFrame({"Conclusion": predictions, "Premises": actuals})
        date = datetime.now().strftime("%d_%m_%y-%H:%M")
        final_df.to_csv(f"Conclusions_{date}.csv")
        print("Generated conclusions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        type=pathlib.Path,
        help="Path to data",
        required=True,
    )
    parser.add_argument(
        "--wandb",
        type=argparse.BooleanOptionalAction,
        help="Enable W&B experiment tracking",
        required=False,
    )

    with open("config-defaults.yaml", "r") as f:
        config = yaml.safe_load(f)

    args = parser.parse_args()
    main(config)
