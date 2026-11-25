import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):

    valid_ids = [2283]

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

    df = df[["CaseID", "DataID", "Offset", "Val"]]

    df.rename(columns={'CaseID': 'stay_id'}, inplace=True)
    df.rename(columns={'DataID': 'item'}, inplace=True)
    df.rename(columns={'Offset': 'charttime'}, inplace=True)
    df.rename(columns={'Val': 'value'}, inplace=True)

    # Handle error manually
    mask = (df['value'] == 280)
    df.loc[mask, 'value'] = 28
    mask = (df['value'] == 0.32)
    df.loc[mask, 'value'] = 30
    
    # Keep 20% - 100%
    valid_mask = (df["value"].ge(20) & df["value"].le(100))
    df = df.loc[valid_mask]
    
    mapping = {2283: 'fio2'}
    df["item"] = df["item"].map(mapping).fillna(df["item"])
    
    base_time = pd.Timestamp("2050-01-01 00:00:00")
    df['charttime'] = (
        base_time
        + pd.to_timedelta(pd.to_numeric(df['charttime'], errors="coerce"),
                          unit="second")
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    df.sort_values(by=['stay_id', 'charttime'], inplace=True)

    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":

    filter_large_csv_by_stay_ids('../../sic/data_float_h_noraw.csv', './chartresp.csv', 'DataID')
    process_columns_rename_time('./chartresp.csv', './chartresp.csv')