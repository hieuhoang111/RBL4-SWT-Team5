import pandas as pd
import numpy as np

def compute_ms(df):
    """
    Computes Mutation Score (MS) = killed / total non-equivalent mutants
    Here, df should contain 'killed' column where 1 = killed, 0 = survived.
    If 'status' == 'LIVE' or similar logic defines equivalent, filter before calling.
    Assuming the input df already excludes equivalent mutants.
    """
    total = len(df)
    if total == 0:
        return 0.0
    killed = df['killed'].sum()
    return killed / total

def compute_mas(df_subset, df_full):
    """
    Computes Mutation Adequacy Score (MAS)
    MAS = MS(subset) / MS(full suite)
    """
    ms_subset = compute_ms(df_subset)
    ms_full = compute_ms(df_full)
    if ms_full == 0:
        return 0.0
    return ms_subset / ms_full

def compute_err(selected_count, total_count):
    """
    Computes Effort Reduction Rate (ERR)
    ERR = 1 - (selected_count / total_count)
    """
    if total_count == 0:
        return 0.0
    return 1.0 - (selected_count / total_count)

def get_top_n_percent_mutants(df, score_col='llm_score', percent=0.7, seed=42):
    """
    Sorts by score_col descending and selects top percent.
    If scores are tied, use random tie-breaking by shuffling first.
    """
    df_shuffled = df.sample(frac=1, random_state=seed)
    df_sorted = df_shuffled.sort_values(by=score_col, ascending=False)
    n_select = int(len(df_sorted) * percent)
    return df_sorted.head(n_select)

def get_random_mutants(df, percent=0.7, seed=42):
    """
    Selects a random subset of mutants.
    """
    n_select = int(len(df) * percent)
    return df.sample(n=n_select, random_state=seed)

def evaluate_project(df, llm_score_col='llm_score', percent=0.7, seed=42):
    """
    Evaluates ERR and MAS for LLM vs Random selection.
    Returns a dictionary of results.
    """
    total_mutants = len(df)
    
    # Full MS
    ms_full = compute_ms(df)
    
    # LLM subset
    df_llm = get_top_n_percent_mutants(df, score_col=llm_score_col, percent=percent, seed=seed)
    mas_llm = compute_mas(df_llm, df)
    err_llm = compute_err(len(df_llm), total_mutants)
    
    # Random subset
    df_rand = get_random_mutants(df, percent=percent, seed=seed)
    mas_rand = compute_mas(df_rand, df)
    err_rand = compute_err(len(df_rand), total_mutants)
    
    return {
        'total_mutants': total_mutants,
        'ms_full': ms_full,
        'mas_llm': mas_llm,
        'err_llm': err_llm,
        'mas_random': mas_rand,
        'err_random': err_rand
    }
