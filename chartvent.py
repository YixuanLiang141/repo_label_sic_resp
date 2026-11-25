import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):

    valid_ids = [2278, 2284, 3040]

    reader = pd.read_csv(input_file, chunksize=chunksize)
    first_chunk = True

    total_rows_kept = 0
    for i, chunk in enumerate(reader):
        filtered_chunk = chunk[chunk[key_col].isin(valid_ids)]
        total_rows_kept += len(filtered_chunk)

        if first_chunk:
            filtered_chunk.to_csv(output_file, index=False, mode='w')
            first_chunk = False
        else:
            filtered_chunk.to_csv(output_file, index=False, mode='a', header=False)

        print(f"✔ Chunk {i+1} done, {len(filtered_chunk)} rows extracted.")

def process_columns_rename_time(data_file, output_file):

    df = pd.read_csv(data_file)

    mask = (df['Val'] > 0)
    df = df[mask]

    df = df[["CaseID", "Offset"]]
    df.rename(columns={'CaseID': 'stay_id'}, inplace=True)
    df.rename(columns={'Offset': 'charttime'}, inplace=True)

    base_time = pd.Timestamp("2050-01-01 00:00:00")
    df['charttime'] = (
        base_time
        + pd.to_timedelta(pd.to_numeric(df['charttime'], errors="coerce"),
                          unit="second")
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    df.sort_values(by=['stay_id', 'charttime'], inplace=True)
    df = df.drop_duplicates(keep='first')

    # 1 hour slot for each record
    time = pd.to_datetime(df["charttime"])

    df["starttime"] = time.dt.floor("h")
    df["endtime"] = df["starttime"] + pd.Timedelta(hours=1)

    for col in ["starttime", "endtime"]:
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df.drop(columns="charttime")
    df.sort_values(by=['stay_id', 'starttime'], inplace=True)

    # Merge overlapped or continuous ranges

    df['starttime'] = pd.to_datetime(
        df['starttime'], errors='coerce', format='mixed'
    )

    df['endtime'] = pd.to_datetime(
        df['endtime'], errors='coerce', format='mixed'
    )

    max_endtime = df.groupby('stay_id')['endtime'].cummax()

    prev_max_endtime = max_endtime.groupby(
        df['stay_id']
    ).shift()

    new_group = (
        df['stay_id'].ne(df['stay_id'].shift())
        | (df['starttime'] > prev_max_endtime)
    )

    df['_group'] = new_group.cumsum()

    df = df.groupby('_group', sort=False).agg(
        stay_id=('stay_id', 'first'),
        starttime=('starttime', 'min'),
        endtime=('endtime', 'max')
    ).reset_index(drop=True)

    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":

    filter_large_csv_by_stay_ids('../../sic/data_float_h_noraw.csv', './chartvent.csv', 'DataID')
    process_columns_rename_time('./chartvent.csv', './chartvent.csv')