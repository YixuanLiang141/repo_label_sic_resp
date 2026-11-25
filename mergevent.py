import pandas as pd


def get_invasive_ventilation(airway_csv, pressure_csv, output_csv):
    cols = ["stay_id", "starttime", "endtime"]

    def read_intervals(path):
        df = pd.read_csv(path, usecols=cols)
        for col in ["starttime", "endtime"]:
            df[col] = pd.to_datetime(
                df[col], format="%Y-%m-%d %H:%M:%S", errors="raise"
            )

        if df[cols].isna().any().any():
            raise ValueError(f"Missing stay_id or time in {path}")
        if (df["endtime"] < df["starttime"]).any():
            raise ValueError(f"End time earlier than start time in {path}")

        return df[df["starttime"] < df["endtime"]]

    def merge_intervals(group):
        merged = []
        for start, end in (
            group.sort_values("starttime")[["starttime", "endtime"]]
            .itertuples(index=False, name=None)
        ):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return merged

    airway = read_intervals(airway_csv)
    pressure = read_intervals(pressure_csv)

    pressure_groups = {
        stay_id: merge_intervals(group)
        for stay_id, group in pressure.groupby("stay_id")
    }

    result = []

    for stay_id, group in airway.groupby("stay_id"):
        a = merge_intervals(group)
        b = pressure_groups.get(stay_id, [])
        i = j = 0

        while i < len(a) and j < len(b):
            start = max(a[i][0], b[j][0])
            end = min(a[i][1], b[j][1])

            if start < end:
                result.append([stay_id, start, end])

            if a[i][1] < b[j][1]:
                i += 1
            else:
                j += 1

    df = pd.DataFrame(result, columns=cols)
    for col in ["starttime", "endtime"]:
        df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

    if output_csv is not None:
        df.to_csv(output_csv, index=False)

    return df

def add_vent(pafi_csv, ventilation_csv, output_csv):
    df = pd.read_csv(pafi_csv)
    vent = pd.read_csv(ventilation_csv)

    times = pd.to_datetime(df["charttime"], errors="raise")
    for col in ["starttime", "endtime"]:
        vent[col] = pd.to_datetime(vent[col], errors="raise")

    df["vent"] = 0

    for stay_id, group in vent.groupby("stay_id"):
        mask = df["stay_id"].eq(stay_id)
        if not mask.any():
            continue

        patient_times = times.loc[mask]
        matched = pd.Series(False, index=patient_times.index)

        for start, end in group[["starttime", "endtime"]].itertuples(
            index=False, name=None
        ):
            matched |= patient_times.ge(start) & patient_times.le(end)

        df.loc[mask, "vent"] = matched.astype(int)

    df.to_csv(output_csv, index=False)

    return df

if __name__ == "__main__":

    #get_invasive_ventilation('rangevent.csv', 'chartvent.csv', 'vent.csv')
    add_vent('pafi.csv', 'vent.csv', 'pafi.csv')