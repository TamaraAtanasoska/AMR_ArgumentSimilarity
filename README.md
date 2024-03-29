# Validating AMR-based Argument Similarity on Novel Datasets

This project reproduces the paper "Explainable Unsupervised Argument Similarity Rating with Abstract Meaning Representation and Conclusion Generation"(Opitz et al., 2021) [(link)](project_docs/OpitzEtAl21.pdf). 

To reproduce the results of the study, two repositories originally written by the author are required: [the more general repository](https://github.com/flipz357/amr-metric-suite) that contains AMR metrics and the [paper-specific repository](https://github.com/Heidelberg-NLP/amr-argument-sim) that contains the AMR metric for argument similarity. As we focus on the results obtained in the paper, we provide both repositories cloned in [```repro_repos/```](repro_repos/). Additionally, we use the [AMR parser](https://github.com/bjascob/amrlib) as used in the paper as a library to turn sentences into graphs. As there were no preserved models for summarisation and exact code and dataset for finetuning, we make our [own take](conclusion_generation/) and keep it as close as possible to the hints given from the researchers that authored the paper. 

Besides reproducing, we extend the original paper. We apply the same method on two other argument similarity corpora (BWS Argument Similarity Corpus ([Thakur et al., 2021](https://arxiv.org/abs/2010.08240)) and Argument Facet Similarity Dataset ([Misra et al., 2016](https://aclanthology.org/W16-3636/))). We also explore how conclusion generation fine-tuning affects the results and how the length of the premises interacts with conclusion generation contributions.

This project is a so-called "Project Module", part of the [Cognitive Systems](https://www.uni-potsdam.de/en/studium/what-to-study/master/masters-courses-from-a-to-z/cognitive-systems) Master program at the [University of Potsdam](https://www.uni-potsdam.de/en/university-of-potsdam). Contributors: [Tamara Atanasoska](https://github.com/TamaraAtanasoska), [Emanuele De Rossi](https://github.com/EmanueleDeRossi1) and [Galina Ryazanskaya](https://github.com/flying-bear).

## Setup

### Environment Recreation 

In the folder ```setup/``` you can find the respective environment replication and package requirements files. There are two options:

  1. You can run ```pip install -r setup/requirements.txt``` to install the necessary packages in your existing environment.

  2. If you are using [conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) to manage your virtual environments, you can replicate and activate the full exact environment with the following commands:

   ```
   conda env create --name <name> --file setup/conda.yml
   conda activate <name>
   ```
   
You might encounter an issue with the package ```mkl_fft``` if you are using conda. You could run the following to install it:
```
conda install -c intel mkl_fft
```

## Generating the S2match Scores and Evaluating with the AMR Metric

### Downloading Word Vectors

S2match needs word vectors to perform the calculation. There is a script included to download Glove word vectors. 

```
cd repro_repos/amr-metric-suite/
./download_glove.sh
```

### Generating S2match Scores

To get the results using the S2match metric which is denoted as "standard" in the paper you can run: 
```
cd repro_repos/amr-metric-suite/py3-Smatch-and-S2match
python smatch/s2match.py -f ../examples/a.txt ../examples/b.txt -cutoff 0.95 --ms
```

This command uses the example files that are already in the folder, they can be replaced with any other file in the right format. The cutoff parameter's value of 0.95 corresponds to the value used in the paper. A high cutoff parameter allows the score to increase only for (near-) paraphrase concepts.

You would need to save the output in a file to be able to use it to evaluate with the AMR metric below. You could either copy-paste the output or run the following complete command: 
```
cd repro_repos/amr-metric-suite/py3-Smatch-and-S2match
python smatch/s2match.py -f ../examples/a.txt ../examples/b.txt -cutoff 0.95 --ms > s2match_scores_standard.txt
```

To get the results using the S2match metric which is denoted as "concept" in the paper you can pass a `weighting_scheme` argument set to 'concept': 
```
cd repro_repos/amr-metric-suite/py3-Smatch-and-S2match
python smatch/s2match.py -f ../examples/a.txt ../examples/b.txt -cutoff 0.95 -weighting_scheme concept --ms
```

To get the results using the S2match metric which is denoted as "structure" in the paper you can pass a `weighting_scheme` argument set to 'structure': 
```
cd repro_repos/amr-metric-suite/py3-Smatch-and-S2match
python smatch/s2match.py -f ../examples/a.txt ../examples/b.txt -cutoff 0.95 -weighting_scheme structure --ms
```

## Using the AMR Parser

If you have set up your environment with [our section](#environment-recreation) about it above, you will already have all the packages installed. If you haven't and you would like to install only the relevant ones for this parser, please take a look at the parser's [installation guide](https://amrlib.readthedocs.io/en/latest/install/). If you only need the parser, it is a better idea to clone the code from the [original repository](https://github.com/bjascob/amrlib) too. 

After installing all the required packages by any of the means, run: 
```
pip install amrlib
```
This will install the library. However, in order to parse, you will also need to pick and download a model to do that with. All the models currently available are found in [this repository](https://github.com/bjascob/amrlib-models). 

We picked to use the [oldest T5-based parse model](https://github.com/bjascob/amrlib-models/releases/tag/model_parse_t5-v0_1_0) available, to be able to get as comparable results with the ones in the paper as possible. 

Once you have picked the model, you need to download it, extract it and rename it. More information can be found [here](https://amrlib.readthedocs.io/en/latest/install/#install-the-models). On Windows, it would be easier to just download the zip file, unzip it and rename the folder instead of the last linking command. 
```
pip show amrlib #copy path where the package is stored 
cd <path-to-where-the-package-is-stored> #copy path from the output of the command above

mkdir data
cd data
tar xzf <model-filename> #copy file here before running command
ln -snf <model-filename>  model_stog
```

To test if the parser is working and the installation is correct, you can run: 
```
cd scripts
python ./test_parse.py 
```

### Parsing the Datasets
To generate amr parses of the datasets one can use `scripts/generate_amr_files.py`. It assumes the dataset is a csv and has two sentence columns to be processed into amr parses. To generate amr files run:
```
python scripts/generate_amr_files.py --data_path_csv <path-to-dataset-csv> --column_name1 <sentence_1_column_name>  --column_name2 <sentence_2_column_name> --out_path <path-to-put-amr-parses>
```
`<path-to-dataset-csv>` should contain the csv with the dataset with the columns indicated as `<sentence_1_column_name>` and  `<sentence_2_column_name>`. The `--column_name` arguments are potional: default names for the columns are `sentence_1` and `sentence_2`. The resulting amr files `amr.src` and `amr.tgt` are put into the folder indicated with `<path-to-put-amr-parses>`. 

Additionally, a batch size can be provided to process the sentences in batches. The default is 5 sentences per batch:

```
python scripts/generate_amr_files.py --data_path_csv <path-to-dataset-csv> --column_name1 <sentence_1_column_name>  --column_name2 <sentence_2_column_name> --batch_size <batch_size> --out_path <path-to-put-amr-parses>
```

## Datasets

### Persuasive Essay Corpus

The original paper [Opitz et al., 2021] uses [Argument Annotated Essays Corpus [Stab & Gurevych, 2017]](https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/2422) for fine-tuning the conclusion T5 generation model. The paper states that “from all premise-conclusion-pairs annotated in this dataset, we retrieved all claims with their annotated premises. In addition, we employ all annotated major claims with their supportive claims as premise-conclusion-pairs” and that “whenever we encounter multiple premises or supportive claims of a single claim, we concatenate them in document order.”

To generate the corpus for fine-tuning T5 summarization on the persuasive essay corpus run:

```
python scripts/generate_persuasive_essay_corpus.py --ann_dir <path-to-dataset>/ArgumentAnnotatedEssays-2.0/brat-project-final --out_path <path-to-output>/premises_conclusions.csv
```

Th script assumes `<path-to-dataset>/ArgumentAnnotatedEssays-2.0` folder contains the contents of the official dataset distribution. 

The script reads the argumentative essay annotation files and extracts major claims, claims, and premises. The script writes to the `<path-to-output>/premises_conclusions.csv` file with 3 columns - `Essay`, `Premises`, `Claim`.

The premises-claim pairs are created as follows: 

1. All claims supporting a major claim are concatenated (separated with `' ### '`) and paired with the major claim. If there are several major claims,  all of the major claims get the same supporting claim sets, e.g `essay0, claim1 ### claim2 ### claim3, major_claim1`
2. All premises supproting a claim are concatenated in the same way and paired with the claim, e.g `essay0, claim1 ### claim2 ### claim3, claim4`
3. All premises supproting a premise are concatenated in the same way and paird with the premies, e.g `essay0, premise1 ### premise2 ### premise3, premise4`

### UKP Dataset
To test the metric on the [UKP Aspect dataset](https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/1998) a renaming scheme needs to be applied to obtain binary scores in accordance with the original article.

```
python scripts/rescale_ukp_dataset.py --ukp_path <path-to-ukp-corpus-tsv> --out_file <out-path>/UKP_corpus.csv
```

The `<path-to-ukp-corpus-tsv>` should be the UKP argument similarity tsv file distributed from the corpus official website. 

The resulting CSV file is written to `<out-path>/UKP_corpus.csv` and contains the following columns: `topic`, `sentence_1`, `sentence_2`, `regression_label_binary`. The sentence and topic columns are copied form the original dataset; the binary label is 1 if the original label is above 'HS' or 'SS' (*highly similar* or *somewhat similar*) and 0 otherwie. No scale of `regression_label` is available for this dataset, only binary scores.

### BWS Dataset
To test the metric on the [BWS dataset](https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/2496) a rescaling scheme needs to be applied to obtain binary scores.

```
python scripts/rescale_bws_dataset.py --bws_path <path-to-bws-corpus-csv> --out_file <out-path>/BWS_corpus.csv
```

The `<path-to-bws-corpus-csv>` should be the BWS argument similarity csv file distributed from the corpus official website. 

The resulting CSV file is written to `<out-path>/BWS_corpus.csv` and contains the following columns: `topic`, `sentence_1`, `sentence_2`, `regression_label_binary`, `regression_label`. The sentence, topic, and regression_label (*score*) columns are copied form the original dataset; the binary label is 1 if the original label is above 0.5 and 0 otherwie.

### AFS Dataset
To test the metric on the [AFS dataset](https://nlds.soe.ucsc.edu/node/44), a rescaling scheme needs to be applied, as the metric is developped for [0,1] similarity schores, and AFS features [0,5] similarity scores.

To merge the three topics of the argument facet similarity dataset into one csv, rescaling the scores from [0,5] to [0,1], along with binary {0, 1} labels run the following comand:

```
python scripts/rescale_AFS_dataset.py --afs_path <path-to-afs-corpus> --out_file <out-path>/AFS_corpus.csv
```

The `<path-to-afs-corpus>` folder should contain the 3 argument similarity csv files distributed from the corpus official website. 

The resulting CSV file is written to `<out-path>/AFS_corpus.csv` and contains the following columns: `topic`, `sentence_1`, `sentence_2`, `regression_label_binary`, `regression_label`. The sentence columns are copied form the original dataset; the topic is ‘GM’, ‘GC’ or ‘DP’ depemding on argument topic; the binary label is 1 if the original label is 4 or 5 and 0 otherwie; and the scaled label is min-max scaled to 0-1 values, scaling being applied per topic.

## Fine-Tuning and Summarisation

The original paper uses conclusions generated by a T5 model, fine-tuned on the Persuasive Essay Corpus discussed above to enhance the s2match scores. The authors also mention trying summarisation, but opting out for the fine-tuned model because of better results. As no models or code were available for neither fine-tuning or summarisation, we made our own attempt of reproducing them, documented below. 

### Weights & Biases

We have introduced [Weights & Biases](https://wandb.ai/site) as platform support to visualize and keep track of our experiments. You could take advantage of this integration by adding the option ```--wandb``` to the fine-tuning or generation commands. 

If you decide to use the option, Weights & Biases will ask you to log in so you can have access to the visualizations and the logging of the runs. You will be prompted to pick an option about how to use W&B, and logging in will subsequently require your W&B API key. It might be more practical for you to already finish this setup before starting the training runs with this option. You can read [here](https://docs.wandb.ai/ref/cli/wandb-login) how to do that from the command line. Creating an account before this step is necessary. 

It is necessay to initialise the entity and project name: [example](https://github.com/TamaraAtanasoska/AMR_ArgumentSimilarity/blob/main/conclusion_generation/fine_tuning/fine-tune.py#L96). You can edit this line to add your own names, and learn more about these settings in the [W&B documentation](https://docs.wandb.ai/ref/python/init). 

### Fine-tuning a T5 Model to Perfom Conclusion Generation 

The code for the fine tuning can found in [conclusion_generation/fine_tuning](conclusion_generation/fine_tuning). It is based almost fully on [this](https://colab.research.google.com/github/abhimishra91/transformers-tutorials/blob/master/transformers_summarization_wandb.ipynb#scrollTo=OKRpFvYhBauC) notebook, with some changes to the way the [W&B](https://wandb.ai/site) parameters are handled and cleaning up of the deprecation errors. The original notebook was listed on the [T5 Huggingface website](https://huggingface.co/docs/transformers/model_doc/t5). 

To fine-tune, you just need to pass the path to the dataset. We used the Persuasive Essay Corpus dataset, for which you can find all details in its [respective section](#persuasive-essay-corpus). 

```
cd conclusion_generation/fine_tuning
python fine-tune.py --data_path <path-to-dataset>
```
The fine-tuned model for inference will be saved at ```conclusion_generation/fine_tuning/models/conclusion_generation_model.pth```.

## Generating Conclusions and Summaries 

You can find our pretrained conclusion generation model [here](https://drive.google.com/file/d/1X0g7T5lZ0UVzNFPA4dZ7WOzKthUVtwXa/view?usp=sharing). The script expects it to be placed in ```conclusion_generation/fine_tuning/models```. The summaries are generated from the T5-base model directly.

The conclusions and summaries we generated from the three datasets we used can be found in [conclusion_generation/generation/datasets](conclusion_generation/generation/datasets).

To generate summaries and conclusions you will need to run the script below with the respective command line argument:

```
cd conclusion_generation/generation
python generate.py --data_path <path-to-dataset> --summaries #or --conclusions
```


## Hyperparameter Search for the Conclusion Generation Model

We looked for the best hyperparameters for the fine-tuning with a W&B sweep. Besides running the command below, you will need to add entity and project name as with the W&B experiment tracking in the code. In order to do that, search for a ```sweep_id``` occurence in [fine_tune.py](conclusion_generation/fine_tuning/fine-tune.py). We have very limited computational resources, so the sweep is with very small ranges and all strictly defined. 

```
cd conclusion_generation/fine_tuning
python fine-tune.py --data_path <path-to-dataset> --wandb_sweep
```

# Evaluation
Once the Amr parses of the corpira, summaries, and conclusions are generated, one ca run the s2match on them to obtain the similarity scores.

## Combining the S2match Scores
The scores are output as a single txt file and the follwoing script allows to combine them into a csv containing all the smatch scores.

```
python scripts/combine_scores.py --data_path_csv <path-to-corpus-csv> --data_path_smatch_standard  <path-to-s2match_scores_standard> --out_path <path-to-put-csv>
```

The <path-to-corpus-csv> should contain a csv file with the original dataset for which the smtach scores were generated. The script combines the corpus scv `df_smatch_scores.csv` with the smatch scores form the txt file. The column name used in the output csv is `standard`. 
  Additionally, one can provide paths to other types of smatch scores:

```
python scripts/combine_scores.py --data_path_csv <path-to-corpus-csv> --data_path_smatch_standard  <path-to-s2match_scores_standard>  --data_path_smatch_struct  <path-to-s2match_scores_struct> --data_path_smatch_concept  <path-to-s2match_scores_concept> --data_path_smatch_conclusion_standard  <path-to-s2match_scores_standard> --data_path_smatch_conclusion_struct  <path-to-s2match_scores_struct> --data_path_smatch_conclusion_concept  <path-to-s2match_scores_concept> --data_path_smatch_summary_standard  <path-to-s2match_scores_standard> --data_path_smatch_summary_struct  <path-to-s2match_scores_struct> --data_path_smatch_summary_concept  <path-to-s2match_scores_concept> --out_path <path-to-put-csv>
```

The columns are then named `standard`, `structure`, `concept`, `conclusion_standard`, `conclusion_structure`, `conclusion_concept`, `summary_standard`, `summary_structure`, `summary_concept`, according to the source of the score and the weighting scheme applied.
  
Finally, the length of the sentences as well as their combined length is calculated for each sentence pair by default and are saved under the names `sentence_1_len`, `sentence_2_len`, `combined_len`. The text column names are assumed to be `sentence_1` and `sentence_2` by default but can be overwritten:
  
```
python scripts/combine_scores.py --data_path_csv <path-to-corpus-csv> --data_path_smatch_standard  <path-to-s2match_scores_standard> --column_name1 <sentence_1_column_name>  --column_name2 <sentence_2_column_name> --out_path <path-to-put-csv>
```
  
The calculation of length can be disabled with passign `F`, `False`, or `0` to `--calculate_length`:
  
```
python scripts/combine_scores.py --data_path_csv <path-to-corpus-csv> --data_path_smatch_standard  <path-to-s2match_scores_standard> --calculate_length False --out_path <path-to-put-csv>
```

## Threshold Crossvalidation and Evaluation
To find a threshold for the similarity values predicting the binary labels, we developed an adaptation of [the original script](https://github.com/TamaraAtanasoska/AMR_ArgumentSimilarity/blob/main/repro_repos/amr-argument-sim/scripts/crval.py) that could be applied to arbitrary datasets. We also slightly modified it to speed up the crossvalidation process.
  
The script assumes a csv with the columns `standard`, `structure`, `concept`, `conclusion_standard`, `conclusion_structure`, `conclusion_concept`, `summary_standard`, `summary_structure`, `summary_concept`.
  
```
python scripts/evaluate/evaluate_dataset.py  --data_path_preds_csv <path-to-ukp-corpus>/df_smatch_scores.csv --fold_size 7 --mixing_value 0.95 --out_path <path-to-ukp-corpus> > <path-to-ukp-corpus>/eval.txt
```
The `--mixing_value` controls the weight given to the propositon vs the conclusion / summary. The default values is `0.95`, so the argument can be omitted. The crossvalidation is preformed by topic, and `--fold_size` must divide the total number of topics.

Additionally, if the argument `--correlation_column` is provided, spearman's correlation coefficient with the column under this name is performed:

```
python scripts/evaluate/evaluate_dataset.py  --data_path_preds_csv <path-to-bws-corpus>/df_smatch_scores.csv --fold_size 2 --correlation_column regression_label --out_path <path-to-bws-corpus> > <path-to-bws-corpus>/eval.txt
```
```
python scripts/evaluate/evaluate_dataset.py  --data_path_preds_csv <path-to-afs-corpus>/df_smatch_scores.csv --fold_size 1 --correlation_column regression_label --out_path <path-to-afs-corpus> > <path-to-afs-corpus>/eval.txt
```
The results are written to the `--out_path` / `results.csv` and contain the columns `f1`, `threshold`, and also `correlation`, `correlation_p` if the argument `--correlation_column` is given. The `threshold` is a weighted average of the fold thresholds.
The verbose version of the evaluation results, along with threshold values for each crossvalidation fold, a weighted threshold, and the correlation results are piped into the `eval.txt`.

## Analyze Results by Length
  
If the `--calculate_length` was enabled for `combine_scores.py` one can run the following script to explore whether the sentence length plays a role in the model performance: 

```
python scripts/evaluate/analyze_by_length.py  --data_path_preds_csv  <path-to-dataset>/df_smatch_scores.csv --data_path_res_csv  <path-to-dataset>/results.csv --out_path <path-to-dataset>
```
The `<path-to-dataset>/df_smatch_scores.csv` is the csv generated by `combine_scores.py` and `<path-to-dataset>/results.csv` generated by `evaluate_dataset.py`. The sentences are binned into lengths (in words) `<100`, `100-200`, `200-250`, `250-300`, `300-400`, `400-500`, and `>500`. F1-score is calculated for each length separately using the threshold calculated by `evaluate_dataset.py`. The results are written into a csv file at `--out_path / eval_by_length.csv`. The columns are the length bins and the rows - the amr similarity methods, along with mean score per bin and total count of examples in the bin.
