import time
import tensorflow as tf
import keras_tuner as kt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import SimpleRNN, GRU, Dense, Dropout, BatchNormalization, Conv1D, Flatten
from tensorflow.keras.optimizers import AdamW, RMSprop
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np
from model_ML import prepare_dataset, evaluate_model

# ------------------------------ #
#   DATA PREPARATION FOR NN      #
# ------------------------------ #
train_set, test_set = prepare_dataset()

X_train = train_set.iloc[:, :-1].values
y_train = train_set.iloc[:, -1].values
X_test = test_set.iloc[:, :-1].values
y_test = test_set.iloc[:, -1].values

X_train_nn = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
X_test_nn = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

# ------------------------------ #
#   Hyperparameter Search        #
# ------------------------------ #

def build_rnn(hp):
    """Optimized RNN Model"""
    model = Sequential([
        SimpleRNN(hp.Int("units", min_value=4, max_value=32, step=4), 
                  activation=hp.Choice("activation", ["swish", "relu", "tanh"]), 
                  input_shape=(X_train_nn.shape[1], 1)),
        BatchNormalization(),
        Dropout(hp.Float("dropout", 0.1, 0.3, step=0.1)),
        Dense(hp.Int("dense_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dense(1)
    ])

    selected_optimizer = hp.Choice("optimizer", ["adamw", "rmsprop"])
    optimizer = {
        "adamw": AdamW(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001])),
        "rmsprop": RMSprop(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001]))
    }

    model.compile(optimizer=optimizer[selected_optimizer], loss="mse")
    return model

def build_gru(hp):
    """Optimized GRU Model"""
    model = Sequential([
        GRU(hp.Int("units", min_value=4, max_value=32, step=4), 
            activation=hp.Choice("activation", ["swish", "relu", "tanh"]), 
            input_shape=(X_train_nn.shape[1], 1)),
        BatchNormalization(),
        Dropout(hp.Float("dropout", 0.1, 0.3, step=0.1)),
        Dense(hp.Int("dense_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dense(1)
    ])
    
    selected_optimizer = hp.Choice("optimizer", ["adamw", "rmsprop"])
    optimizer = {
        "adamw": AdamW(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001])),
        "rmsprop": RMSprop(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001]))
    }

    model.compile(optimizer=optimizer[selected_optimizer], loss="mse")
    return model

def build_cnn_rnn(hp):
    """Optimized CNN + RNN Model"""
    model = Sequential([
        Conv1D(filters=hp.Int("filters", min_value=4, max_value=16, step=4), 
               kernel_size=hp.Int("kernel_size", min_value=2, max_value=4), 
               activation="swish", input_shape=(X_train_nn.shape[1], 1)),
        BatchNormalization(),
        SimpleRNN(hp.Int("rnn_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dropout(hp.Float("dropout", 0.1, 0.3, step=0.1)),
        Dense(hp.Int("dense_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dense(1)
    ])
    
    model.compile(optimizer=AdamW(learning_rate=0.0003), loss="mse")
    return model

def build_cnn_gru(hp):
    """Optimized CNN + GRU Model"""
    model = Sequential([
        Conv1D(filters=hp.Int("filters", min_value=4, max_value=16, step=4), 
               kernel_size=hp.Int("kernel_size", min_value=2, max_value=4), 
               activation="swish", input_shape=(X_train_nn.shape[1], 1)),
        BatchNormalization(),
        GRU(hp.Int("gru_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dropout(hp.Float("dropout", 0.1, 0.3, step=0.1)),
        Dense(hp.Int("dense_units", min_value=4, max_value=16, step=4), activation="swish"),
        Dense(1)
    ])
    
    model.compile(optimizer=AdamW(learning_rate=0.0003), loss="mse")
    return model

def build_mlp(hp):
    """Optimized MLP Model"""
    model = Sequential([
        Dense(hp.Int("dense_1", min_value=8, max_value=32, step=8), activation="swish", input_shape=(X_train.shape[1],)),
        BatchNormalization(),
        Dropout(hp.Float("dropout", 0.1, 0.3, step=0.1)),
        Dense(hp.Int("dense_2", min_value=4, max_value=16, step=4), activation="swish"),
        Dense(1)
    ])

    selected_optimizer = hp.Choice("optimizer", ["adamw", "rmsprop"])
    optimizer = {
        "adamw": AdamW(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001])),
        "rmsprop": RMSprop(learning_rate=hp.Choice("learning_rate", [0.0001, 0.0003, 0.001]))
    }

    model.compile(optimizer=optimizer[selected_optimizer], loss="mse")
    return model

# ------------------------------ #
#   Run Hyperparameter Search    #
# ------------------------------ #
def run_tuner(model_builder, model_name):
    tuner = kt.Hyperband(
        model_builder,
        objective="val_loss",
        max_epochs=50,
        factor=3,
        directory="kt_search",
        project_name=model_name
    )

    early_stopping = EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)

    tuner.search(X_train_nn, y_train, epochs=50, batch_size=16, 
                 validation_data=(X_test_nn, y_test), callbacks=[early_stopping], verbose=1)

    best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]
    best_model = tuner.hypermodel.build(best_hps)

    return best_model, best_hps

# ------------------------------ #
#      Train & Evaluate Models   #
# ------------------------------ #
if __name__ == "__main__":
    start_time = time.time()

    models_to_tune = {
        "RNN": build_rnn,
        "GRU": build_gru,
        "CNN+RNN": build_cnn_rnn,
        "CNN+GRU": build_cnn_gru,
        "MLP": build_mlp
    }

    nn_results = {}

    for model_name, model_builder in models_to_tune.items():
        print(f"Tuning {model_name}...")
        best_model, best_hps = run_tuner(model_builder, model_name)

        best_model.fit(X_train_nn, y_train, epochs=50, batch_size=16, 
                       validation_data=(X_test_nn, y_test), callbacks=[EarlyStopping(monitor="val_loss", patience=10)], verbose=2)

        y_pred = best_model.predict(X_test_nn)
        nn_results[model_name] = evaluate_model(y_test, y_pred.flatten())

    for key, value in nn_results.items():
        print(f"{key} test scores")
        for key2, value2 in value.items():
            print(f"\t{key2}: {value2}")

    print(f"Total training time: {time.time() - start_time:.2f} seconds")
