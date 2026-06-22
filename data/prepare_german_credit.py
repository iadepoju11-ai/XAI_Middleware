"""
Prepare German Credit dataset for use in training and fairness evaluation.

Run once after download:
  python data/prepare_german_credit.py

Outputs:
  data/german_credit/german_credit.csv        (raw, already present)
  data/german_credit/german_credit_clean.csv  (encoded, model-ready)
"""
import ssl
ssl._create_default_https_context = ssl._create_unverified_context  # corporate SSL fix

import pandas as pd
import os

RAW = "data/german_credit/german_credit.csv"
OUT = "data/german_credit/german_credit_clean.csv"


def derive_sex(personal_status: pd.Series) -> pd.Series:
    """Binary sex attribute: 1 = male, 0 = female. Used ONLY for fairness monitoring."""
    return personal_status.str.startswith("male").astype(int)


def prepare():
    df = pd.read_csv(RAW)
    print(f"Raw: {df.shape}")

    # Derive protected attribute (fairness use only — excluded from model features)
    df["sex"] = derive_sex(df["personal_status"])

    # Binary target: 1 = good credit, 0 = bad credit
    df["target"] = (df["class"] == "good").astype(int)

    # Drop raw columns not used in modelling
    df = df.drop(columns=["class"])

    df.to_csv(OUT, index=False)
    print(f"Clean: {df.shape}  ->  {OUT}")
    print(f"Target distribution: {df['target'].value_counts().to_dict()}")
    print(f"Sex distribution: {df['sex'].value_counts().to_dict()}")


if __name__ == "__main__":
    prepare()
