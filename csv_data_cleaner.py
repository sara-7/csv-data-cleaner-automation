import pandas as pd
import os


def clean_column_names(df):
    # Standardize column names to lowercase with underscores
    # Example: 'Bill Length MM' becomes 'bill_length_mm'
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace("/", "_")
    )

    return df


def clean_text_columns(df):
    # Strip extra whitespace and replace common placeholders with real missing values
    df = df.copy()

    text_columns = df.select_dtypes(include=["object"]).columns

    missing_placeholders = ["", "nan", "None", "none", "NULL", "null", "NaN", "N/A", "n/a"]

    for col in text_columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.replace(r"\s+", " ", regex=True)
        df[col] = df[col].replace(missing_placeholders, pd.NA)

    return df


def convert_data_types(df):
    # Try converting columns to numeric types where possible
    # Try converting columns with 'date' or 'time' in their name to datetime
    df = df.copy()

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    for col in df.columns:
        if "date" in col or "time" in col:
            # Use errors='coerce' to replace unparseable values with NaT
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def handle_missing_values(df):
    # Fill missing numeric values with the column median
    # Fill missing text values with 'Unknown'
    df = df.copy()

    numeric_columns = df.select_dtypes(include=["number"]).columns
    text_columns = df.select_dtypes(include=["object"]).columns

    for col in numeric_columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    for col in text_columns:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna("Unknown")

    return df


def handle_outliers(df):
    # Detect and cap outliers in numeric columns using the IQR method
    # Values below the lower bound or above the upper bound are clipped
    df = df.copy()

    numeric_columns = df.select_dtypes(include=["number"]).columns
    outliers_summary = {}

    for col in numeric_columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
        outliers_summary[col] = int(outliers_count)

        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    return df, outliers_summary


def generate_report(
    original_df,
    cleaned_df,
    missing_before,
    missing_after,
    duplicates_removed,
    outliers_summary,
    output_file,
    report_name
):
    # Write a structured text report summarizing all cleaning steps and results
    with open(report_name, "w", encoding="utf-8") as report:
        report.write("CSV Data Cleaning Report\n")
        report.write("=" * 30 + "\n\n")

        report.write("Original Data Shape:\n")
        report.write(f"Rows: {original_df.shape[0]}\n")
        report.write(f"Columns: {original_df.shape[1]}\n\n")

        report.write("Cleaned Data Shape:\n")
        report.write(f"Rows: {cleaned_df.shape[0]}\n")
        report.write(f"Columns: {cleaned_df.shape[1]}\n\n")

        report.write("Cleaning Steps Applied:\n")
        report.write("- Standardized column names\n")
        report.write("- Removed duplicated rows\n")
        report.write("- Cleaned text columns and extra spaces\n")
        report.write("- Converted data types where possible\n")
        report.write("- Handled missing values\n")
        report.write("- Handled outliers using IQR method\n")
        report.write("- Saved a new cleaned CSV file\n\n")

        report.write("Duplicates Removed:\n")
        report.write(f"{duplicates_removed}\n\n")

        report.write("Missing Values Before Cleaning:\n")
        report.write(str(missing_before))
        report.write("\n\n")

        report.write("Missing Values After Cleaning:\n")
        report.write(str(missing_after))
        report.write("\n\n")

        report.write("Outliers Summary:\n")
        for col, count in outliers_summary.items():
            report.write(f"{col}: {count} outliers handled\n")
        report.write("\n")

        report.write("Data Description:\n")
        report.write(str(cleaned_df.describe(include="all")))
        report.write("\n\n")

        report.write("Output File:\n")
        report.write(output_file)

    return report_name


def clean_csv_file(input_file):
    # Main function: read, clean, save, and report

    # Validate that the file exists
    if not os.path.exists(input_file):
        print("File not found. Please check the file path.")
        return

    # Validate that the file is a CSV
    if not input_file.lower().endswith(".csv"):
        print("Invalid file type. Please provide a CSV file.")
        return

    # Read the original CSV file
    df = pd.read_csv(input_file)

    # Keep a copy of the original data for comparison in the report
    original_df = df.copy()

    # Record missing values before any cleaning
    missing_before = df.isnull().sum()

    # Count duplicate rows before removal
    duplicates_before = df.duplicated().sum()

    # Step 1: Standardize column names
    df = clean_column_names(df)

    # Step 2: Remove duplicate rows
    df = df.drop_duplicates()

    # Step 3: Clean text columns
    df = clean_text_columns(df)

    # Step 4: Convert columns to appropriate data types
    df = convert_data_types(df)

    # Step 5: Fill in missing values
    df = handle_missing_values(df)

    # Step 6: Handle outliers
    df, outliers_summary = handle_outliers(df)

    # Record missing values after cleaning for comparison
    missing_after = df.isnull().sum()

    # Calculate how many duplicates were removed
    duplicates_after = df.duplicated().sum()
    duplicates_removed = duplicates_before - duplicates_after

    # Build output file paths based on the input file name
    file_name, _ = os.path.splitext(input_file)
    output_file = file_name + "_cleaned.csv"
    report_file = file_name + "_cleaning_report.txt"

    # Save the cleaned data to a new CSV file
    df.to_csv(output_file, index=False)

    # Generate and save the cleaning report
    generate_report(
        original_df,
        df,
        missing_before,
        missing_after,
        duplicates_removed,
        outliers_summary,
        output_file,
        report_file
    )

    print("Cleaning completed successfully.")
    print(f"Cleaned file saved as: {output_file}")
    print(f"Report saved as: {report_file}")


if __name__ == "__main__":
    input_file = input("Enter CSV file path: ")
    clean_csv_file(input_file)