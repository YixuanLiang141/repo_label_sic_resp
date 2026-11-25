import pandas as pd

def merge_sort(csv1: str, csv2: str, output_file: str):

    df1 = pd.read_csv(csv1)
    df2 = pd.read_csv(csv2)

    # Check column names and order
    if list(df1.columns) != list(df2.columns):
        raise ValueError("Different column names or order")

    merged_df = pd.concat([df1, df2], ignore_index=True)

    merged_df.sort_values(by=['stay_id', 'charttime'], inplace=True)

    merged_df = merged_df.drop_duplicates(keep='first')

    merged_df.to_csv(output_file, index=False)

    print(f"Done, {len(merged_df)} rows saved to: {output_file}")

def calculate_pf_ratio(input_csv, output_csv, fio2_unit):
    if fio2_unit not in {"fraction", "percent"}:
        raise ValueError("fio2_unit must be 'fraction' or 'percent'")

    df = pd.read_csv(input_csv)

    df["charttime"] = pd.to_datetime(
        df["charttime"], format="%Y-%m-%d %H:%M:%S", errors="raise"
    )

    keys = ["stay_id", "charttime"]

    # remove other columns if pao2/fio2 exists
    has_ratio = (
        df["item"].eq("pao2/fio2")
        .groupby([df["stay_id"], df["charttime"]])
        .transform("any")
    )
    df = df.loc[~has_ratio | df["item"].eq("pao2/fio2")].copy()
    df = df.reset_index(drop=True)

    # extract PaO2 and FiO2
    pa = df.loc[df["item"].eq("pao2"), keys + ["value"]].copy()
    pa["_source_row"] = pa.index
    pa["_pao2"] = pd.to_numeric(pa.pop("value"), errors="coerce")
    pa = pa.loc[pa["_pao2"].gt(0)]

    fi = df.loc[df["item"].eq("fio2"), keys + ["value"]].copy()
    fi["_fio2"] = pd.to_numeric(fi.pop("value"), errors="coerce")

    if fio2_unit == "percent":
        fi["_fio2"] = fi["_fio2"] / 100

    # if multiple FiO2 records exist at the same time, use the last one
    fi = fi.drop_duplicates(keys, keep="last")
    fi = fi.rename(columns={"charttime": "_fio2_time"})

    if not pa.empty and not fi.empty:
        matched = pd.merge_asof(
            pa.sort_values("charttime"),
            fi.sort_values("_fio2_time"),
            left_on="charttime",
            right_on="_fio2_time",
            by="stay_id",
            direction="backward",
            tolerance=pd.Timedelta(hours=4),
            allow_exact_matches=True,
        )
        matched = matched.dropna(subset=["_fio2"])

        new_rows = df.loc[matched["_source_row"].to_numpy()].copy()
        new_rows["item"] = "pao2/fio2"
        new_rows["value"] = (
            matched["_pao2"] / matched["_fio2"]
        ).to_numpy()

        df = pd.concat([df, new_rows], ignore_index=True)

    df = df.sort_values(
        ["stay_id", "charttime", "item"], kind="stable"
    ).reset_index(drop=True)
    #df["charttime"] = df["charttime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    mask = (df['item'] == 'pao2/fio2')
    df = df[mask]
    df = df[['stay_id','charttime','value']]
    df.rename(columns={'value': 'pao2fio2ratio'}, inplace=True)

    df.to_csv(output_csv, index=False)

    return df

if __name__ == "__main__":
    merge_sort('./chartresp.csv', './labresp.csv', './resp.csv')
    calculate_pf_ratio('./resp.csv', './pafi.csv', 'percent')