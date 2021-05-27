# -*- coding: utf-8 -*-
"""MNIST_GRU.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/srijayjk/Deep-Learning/blob/master/MNIST_GRU.ipynb
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.datasets import mnist

(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = x_train.astype("float32") / 255.0
x_test = x_test.astype("float32") / 255.0

model = keras.Sequential()
model.add(keras.layers.GRU(100, input_shape=(None, 28), activation='tanh', return_sequences=True))
model.add(keras.layers.Dropout(0.5))
model.add(keras.layers.GRU(100, activation='tanh'))
model.add(keras.layers.Dropout(0.5))
model.add(keras.layers.Dense(100, activation='tanh'))
model.add(keras.layers.Dense(10, activation='sigmoid'))
model.summary()

model.compile(optimizer='adam', loss='SparseCategoricalCrossentropy', metrics=['accuracy'])
model.fit(x_train, y_train, batch_size=128, epochs=5, validation_data=(x_test, y_test))