import os
import db
import pandas as pd
import numpy as np
import pickle
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, mean_absolute_error, mean_squared_error, r2_score
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.neighbors import KNeighborsRegressor
from catboost import CatBoostRegressor
from sklearn.neural_network import MLPRegressor

def mape(y_true, y_pred):
    """ Mean Absolute Percentage Error (MAPE) """
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def smape(y_true, y_pred):
    """ Symmetric Mean Absolute Percentage Error (SMAPE) """
    return np.mean(2 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred))) * 100

def wmape(y_true, y_pred):
    """ Weighted Mean Absolute Percentage Error (WMAPE) """
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

def rmse(y_true, y_pred):
    """ Root Mean Squared Error (RMSE) """
    return np.sqrt(mean_squared_error(y_true, y_pred))

def r2(y_true, y_pred):
    """ R² Score """
    return r2_score(y_true, y_pred)

def prepare_dataset():
    CACHE_FILE = "volatility_cache.pkl"

    if not os.path.exists(CACHE_FILE):
        print("Fetched volatility data from API and cached it.")
        db.fetch_and_cache_volatility()

    with open(CACHE_FILE, "rb") as f:
        result = pickle.load(f)

    # Convert to DataFrame
    df = pd.DataFrame(result)
    df['Date'] = pd.to_datetime(df['Date'])
    df.dropna(inplace=True)
    df_size = df.shape[0]
    print(df.head())

    window_size = 21
    loop_size = df_size - window_size
    train_size = int(loop_size * 0.8)
    test_size = loop_size - train_size

    print(f"sample size: {df_size}")
    print(f"loop size: {loop_size}")
    print(f"train size: {train_size}")
    print(f"test size: {test_size}")

    train_set = pd.DataFrame(np.zeros((train_size, window_size + 1)), 
                  columns=[f'Column_{i+1}' for i in range(window_size + 1)])
    test_set = pd.DataFrame(np.zeros((test_size, window_size + 1)), 
                  columns=[f'Column_{i+1}' for i in range(window_size + 1)])

    for i in range(loop_size):
        if i < train_size:
            for j in range(window_size):
                train_set.iloc[i, j] = df.loc[i + j, 'Log_Returns']
            train_set.iloc[i, window_size] = df.loc[i + window_size, 'Volatility']
        else:
            for j in range(window_size):
                test_set.iloc[i - train_size, j] = df.loc[i + j, 'Log_Returns']
            test_set.iloc[i - train_size, window_size] = df.loc[i + window_size, 'Volatility']
    
    print(train_set.head())
    print(test_set.head())

    return train_set, test_set

def grid_search(model, param, scorer, X_train, y_train, ):
    grid_search = GridSearchCV(
        model, param, cv=5, scoring=scorer, verbose=2, n_jobs=-1, return_train_score=True
    )
    grid_search.fit(X_train, y_train)

    return grid_search.best_estimator_, grid_search.best_params_, -grid_search.best_score_

def evaluate_model(y_true, y_pred):
    """ Compute multiple performance metrics """
    return {
        "MAPE": mape(y_true, y_pred),
        "SMAPE": smape(y_true, y_pred),
        "WMAPE": wmape(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
        "MAE": mean_absolute_error(y_true, y_pred),
        "R2 Score": r2(y_true, y_pred)
    }

def model_test(model, X_test, y_test):
    y_pred = model.predict(X_test)
    return evaluate_model(y_test, y_pred)

if __name__ == "__main__":
    train_set, test_set = prepare_dataset()
    mape_scorer = make_scorer(mape, greater_is_better=False)
    X_train = train_set.iloc[:, :-1]
    y_train = train_set.iloc[:, -1]
    X_test = test_set.iloc[:, :-1]
    y_test = test_set.iloc[:, -1]
    result = {}

    gpr = GaussianProcessRegressor(n_restarts_optimizer=10)
    param_grid = {
        "kernel": [RBF(length_scale=l) + WhiteKernel(noise_level=n, noise_level_bounds=(1e-6, 1e2)) 
                for l in [1.0, 5.0, 10.0] 
                for n in [0.1, 1.0, 10.0]],
        "alpha": [1e-3, 1e-2, 1e-1, 1.0, 10.0],
        "optimizer": ["fmin_l_bfgs_b", None]
    }
    best_model, best_param, best_score = grid_search(gpr, param_grid, mape_scorer, X_train, y_train)
    result.update({"GBR": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})
    
    svr = SVR()
    param_grid = {
        "C": [0.1, 1, 10, 100],
        "epsilon": [0.001, 0.01, 0.1, 0.5],
        "gamma": ["scale", "auto", 0.01, 0.1, 1.0],
        "kernel": ["rbf", "poly", "sigmoid"]
    }
    best_model, best_param, best_score = grid_search(svr, param_grid, mape_scorer, X_train, y_train)
    result.update({"SVR": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    rf = RandomForestRegressor(random_state=42)
    param_grid = {
        "n_estimators": [50, 100, 300],
        "max_depth": [5, 10, 20, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 5],
        "max_features": ["sqrt", "log2", None]
    }
    best_model, best_param, best_score = grid_search(rf, param_grid, mape_scorer, X_train, y_train)
    result.update({"RF": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    knn = KNeighborsRegressor()
    param_grid = {
        "n_neighbors": [3, 5, 10, 20],
        "weights": ["uniform", "distance"],
        "metric": ["euclidean", "manhattan", "minkowski"]
    }
    best_model, best_param, best_score = grid_search(knn, param_grid, mape_scorer, X_train, y_train)
    result.update({"KNN": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    xgb = XGBRegressor(random_state=42)
    param_grid = {
        "n_estimators": [50, 100, 300],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "max_depth": [3, 5, 10],
        "subsample": [0.6, 0.8, 1.0],
        "colsample_bytree": [0.6, 0.8, 1.0]
    }
    best_model, best_param, best_score = grid_search(xgb, param_grid, mape_scorer, X_train, y_train)
    result.update({"XGB": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    lgbm = LGBMRegressor()
    param_grid = {
        "num_leaves": [10, 20, 50, 100],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "n_estimators": [50, 100, 300],
        "max_depth": [3, 5, 10],
        "subsample": [0.6, 0.8, 1.0]
    }
    best_model, best_param, best_score = grid_search(lgbm, param_grid, mape_scorer, X_train, y_train)
    result.update({"LGBM": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    catboost = CatBoostRegressor(verbose=0)
    param_grid = {
        "iterations": [50, 100, 300],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "depth": [3, 5, 10],
        "l2_leaf_reg": [1, 3, 5, 10]
    }
    best_model, best_param, best_score = grid_search(catboost, param_grid, mape_scorer, X_train, y_train)
    result.update({"CatBoost": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    mlp = MLPRegressor(max_iter=500)
    param_grid = {
        "hidden_layer_sizes": [(50,), (100,), (50,50)],
        "activation": ["relu", "tanh"],
        "alpha": [0.0001, 0.001, 0.01],
        "learning_rate": ["constant", "adaptive"]
    }
    best_model, best_param, best_score = grid_search(mlp, param_grid, mape_scorer, X_train, y_train)
    result.update({"MLP": [best_model, best_param, best_score, model_test(best_model, X_test, y_test)]})

    for key, value in result.items():
        print(f"{key}")
        print(f"\tBest param: {value[1]}")
        print(f"\tBest MAPE score: {value[2]}")
        print(f"\tTest scores")
        for key2, value2 in value[3].items():
            print(f"\t\t{key2}: {value2}")
