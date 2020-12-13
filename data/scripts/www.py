import os
import re
import pandas as pd
import frontmatter
import numpy as np
import json
import matplotlib.pyplot as plt

DIRNAME = os.path.dirname(__file__)
WWW_SHIPS_PATH = os.path.join(DIRNAME, "../../www/views/ships")
WWW_IMG_PATH = os.path.join(DIRNAME, "../../www/assets/img")
WWW_THETIS_DATA_PATH = os.path.join(DIRNAME, '../../www/views/_data/thetis')
WWW_DOC_PATH = os.path.join(DIRNAME, '../../www/views/doc/')
THETIS_CSV_PATH = os.path.join(DIRNAME, "../files_computed/thetis_all_with_computed.csv")

def get_frontmatter_df(only_out_of_scope=False, exclude_out_of_scope=True):
    all_ships = []
    for filename in os.listdir(WWW_SHIPS_PATH):
        if not re.match(r".*-(\d+)\.md", filename):
            continue
        ship_frontmatter = frontmatter.load(os.path.join(WWW_SHIPS_PATH, filename))
        all_ships.append({ **ship_frontmatter.metadata })
    df = pd.DataFrame(all_ships)
    if only_out_of_scope:
        df = df[df.outOfScope == True]
    elif exclude_out_of_scope:
        df = df[df.outOfScope != True]
    return df

def camelCase(st):
    output = ''.join(x for x in st.title() if x.isalnum())
    return output[0].lower() + output[1:]

def monitoring_methods(row):
    monitoring_methods = []
    for letter in ["a", "b", "c", "d"]:
        if not pd.isna(row[f"monitoring_method_{letter}"]):
            monitoring_methods.append(letter)
    return monitoring_methods

def write_thetis_jsons():
    df_thetis = pd.read_csv(THETIS_CSV_PATH).replace({np.nan: None})
    df_thetis["monitoring_methods"] = df_thetis.apply(lambda row: monitoring_methods(row), axis=1)
    for letter in ["a", "b", "c", "d"]:
        del df_thetis[f"monitoring_method_{letter}"]
    df_thetis.columns = df_thetis.columns.map(lambda x: camelCase(x))
    filenames = os.listdir(WWW_SHIPS_PATH)
    matching_filenames = [fn for fn in filenames if re.match(r".*-(\d+)\.md", fn)]
    imos = [re.match(r".*-(\d+)\.md", fn).groups()[0] for fn in matching_filenames]
    print(f"iterating over {len(imos)} IMOs to write THETIS json files")
    for imo in imos:
        data = {}
        for _idx, row in df_thetis[df_thetis.imo == int(imo)].iterrows():
            row_dict = row.to_dict()
            data[str(int(row_dict['reportingPeriod']))] = row_dict
        path = os.path.join(WWW_THETIS_DATA_PATH, f"thetis-{imo}.json")
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

def export_monitoring_methods_graph():
    plt.clf()
    df_thetis = pd.read_csv(THETIS_CSV_PATH, dtype={"imo": str}).replace({np.nan: None})
    df_thetis["monitoring_methods"] = df_thetis.apply(lambda row: monitoring_methods(row), axis=1)
    for letter in ["a", "b", "c", "d"]:
        del df_thetis[f"monitoring_method_{letter}"]
    md_imos = get_frontmatter_df(exclude_out_of_scope=True).imo.apply(lambda x: str(x))
    df_ferries = df_thetis[df_thetis.imo.isin(md_imos)]
    df_ferries_2019 = df_ferries[df_ferries.reporting_period == 2019]
    data = df_ferries_2019.monitoring_methods.apply(lambda ms: "-".join([msc.capitalize() for msc in ms]) or "n/a").value_counts()
    plot = data.plot.bar()
    plot.set_xlabel("Monitoring Method")
    plot.set_ylabel(f"Ships count (total: {df_ferries_2019.shape[0]})")
    path = os.path.join(WWW_IMG_PATH, "doc_monitoring_methods_distribution.svg")
    plot.figure.savefig(path, format="svg")
    print(f"rewrote {path}")

def export_technical_efficiency_graph_and_json():
    df = pd.read_csv(THETIS_CSV_PATH, dtype={"imo": str})
    df = df[df.reporting_period == 2019]
    df = df[df.imo.isin(list(get_frontmatter_df().imo.apply(lambda x: str(x))))]
    plt.clf()
    plot = df.plot.scatter(
        x="annual_computed_average_co2_emissions_per_transport_work_pax_km",
        y="technical_efficiency_eiv",
        xlim=(0,1000),
        ylim=(0,200)
    )
    plot.set_ylabel("EIV - gCO₂/ton/n.mile")
    plot.set_xlabel("Average emissions reported - gCO₂/km/person")
    path = os.path.join(WWW_IMG_PATH, "doc_technical_efficiency_correlation.svg")
    plot.figure.savefig(path, format="svg")
    path = os.path.join(WWW_DOC_PATH, f"technical_efficiency.11tydata.json")
    with open(path, 'w') as f:
        json.dump({
            "shipsWithEivCount": df[~df.technical_efficiency_eiv.isnull()].shape[0],
            "shipsWithEediCount": df[~df.technical_efficiency_eedi.isnull()].shape[0],
            "shipsWithoutTechnicalEfficiencyCount": df[df.technical_efficiency_eiv.isnull() & df.technical_efficiency_eedi.isnull()].shape[0]
        }, f, indent=2)
    print(f"rewrote {path}")

if __name__ == "__main__":
    # print(get_frontmatter_df().head())
    # write_thetis_jsons()
    # export_monitoring_methods_graph()
    export_technical_efficiency_graph_and_json()
