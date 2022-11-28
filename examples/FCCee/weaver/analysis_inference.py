import sys

# Optional
nCPUS = 8

model_dir = "/eos/experiment/fcc/ee/jet_flavour_tagging/pre_fall2022_training/IDEA/selvaggi_2022Oct30/"
weaver_preproc = "{}/preprocess_fccee_flavtagging_edm4hep_v2.json".format(model_dir)
weaver_model = "{}/fccee_flavtagging_edm4hep_v2.onnx".format(model_dir)

## extract input variables/score name and ordering from json file
import json

variables, scores = [], []
f = open(weaver_preproc)
data = json.load(f)
for varname in data["pf_features"]["var_names"]:
    variables.append(varname)
for scorename in data["output_names"]:
    scores.append(scorename)

f.close()
# convert to tuple
variables = tuple(variables)

from examples.FCCee.weaver.config import definition, alias, variables_jet

# first aliases
for var, al in alias.items():
    print(var, al)

# then funcs
for varname in variables:
    if varname not in definition:
        print("ERROR: {} variables was not defined.".format(varname))
        sys.exit()

# Mandatory: RDFanalysis class where the use defines the operations on the TTree
class RDFanalysis:
    # __________________________________________________________
    # Mandatory: analysers funtion to define the analysers to process, please make sure you return the last dataframe, in this example it is df2
    def analysers(df):

        get_weight_str = "JetFlavourUtils::get_weights("
        for var in variables:
            get_weight_str += "{},".format(var)
        get_weight_str = "{})".format(get_weight_str[:-1])

        from ROOT import JetFlavourUtils

        weaver = JetFlavourUtils.setup_weaver(
            weaver_model,  # name of the trained model exported
            weaver_preproc,  # .json file produced by weaver during training
            variables,
        )

        ### COMPUTE THE VARIABLES FOR INFERENCE OF THE TRAINING MODEL
        # first aliases
        for var, al in alias.items():
            df = df.Alias(var, al)
        # then funcs
        for var, call in definition.items():
            df = df.Define(var, call)

        ##### RUN INFERENCE and cast scores (fixed by the previous section)
        df = df.Define("MVAVec", get_weight_str)

        for i, scorename in enumerate(scores):
            df = df.Define(
                scorename, "JetFlavourUtils::get_weight(MVAVec, {})".format(i)
            )

        df2 = (
            df
            ##### COMPUTE OBSERVABLES FOR ANALYSIS
            # if not changing training etc... but only interested in the analysis using a trained model (fixed classes), you should only operate in this section.
            # if you're interested in saving variables used for training don't need to compute them again, just
            # add them to the list in at the end of the code
            # EXAMPLE
            # EVENT LEVEL
            # extra jet kinematics (not defined earlier)
            .Define("recojet_pt", "JetClusteringUtils::get_pt(jets_ee_genkt)")
            .Define("recojet_e", "JetClusteringUtils::get_e(jets_ee_genkt)")
            .Define("recojet_mass", "JetClusteringUtils::get_m(jets_ee_genkt)")
            .Define("recojet_phi", "JetClusteringUtils::get_phi(jets_ee_genkt)")
            .Define("recojet_theta", "JetClusteringUtils::get_theta(jets_ee_genkt)")
            # counting types of particles composing the jet
        )

        return df2

    # __________________________________________________________
    # SAVE PREDICTIONS & OBSERVABLES FOR ANALYSIS
    # Mandatory: output function, please make sure you return the branchlist as a python list
    def output():
        branchList = [
            # predictions
            "recojet_isG",
            "recojet_isQ",
            "recojet_isS",
            "recojet_isC",
            "recojet_isB",
            # observables
            "recojet_mass",
            "recojet_e",
            "recojet_pt",
        ]

        # add jet variables defined in config
        branchList += list(variables_jet.keys())
        branchList += ["event_invariant_mass", "event_njet"]

        return branchList
