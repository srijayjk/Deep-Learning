from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf

tf.__version__

# To generate GIFs for illustration
!pip install imageio

import glob
import imageio
import matplotlib.pyplot as plt
import numpy as np
import os
import PIL
from tensorflow.keras import layers
import time

from IPython import display

"""### Load and prepare the dataset
You will use the MNIST dataset to train the generator and the discriminator. The generator will generate handwritten digits resembling the MNIST data.
You can also repeat the exercise for other avaliable variations of the MNIST dataset such as: EMNIST, Fashio-MNIST or KMNIST.
"""

(train_images, train_labels), (_, _) = tf.keras.datasets.mnist.load_data()

train_images = train_images.reshape(train_images.shape[0], 28, 28, 1).astype('float32')
train_images = (train_images - 127.5) / 127.5  # Normalize the images to [-1, 1]

BUFFER_SIZE = 60000
BATCH_SIZE = 256

# Batch and shuffle the data
train_dataset = tf.data.Dataset.from_tensor_slices(train_images).shuffle(BUFFER_SIZE).batch(BATCH_SIZE)

"""## Create the models
### The Generator
The generator uses `tf.keras.layers.Conv2DTranspose` (fractional-strided convolutional) layers to produce an image from an input noise vector. Start with a fully connected layer that takes this vector as input, then upsample several times until you reach the desired image size of $28\times 28 \times 1$. Utilize the `tf.keras.layers.LeakyReLU` activation and batch normalization for each intermediate layer, except the output layer which should use tanh.
"""

def make_generator_model():
    model = tf.keras.Sequential()
    model.add(layers.Dense(7*7*256, use_bias=False, input_shape=(100,))) # Fully connected layer: model.add(layers.Dense(#*#*#, use_bias=False, input_shape=(100,)))
    model.add(layers.BatchNormalization()) # Batch norm
    model.add(layers.LeakyReLU()) # Activation function

    model.add(layers.Reshape((7, 7, 256))) # Reshape
    assert model.output_shape == (None, 7, 7, 256) # Note: None is the batch size

    # Layer 2: Hint use layers.Conv2DTranspose with 5x5 kernels and appropriate stride

    model.add(layers.Conv2DTranspose(128, (5, 5), strides=(1, 1), padding='same', use_bias=False))
    assert model.output_shape == (None, 7, 7, 128)
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU())

    # Layer 3
    model.add(layers.Conv2DTranspose(64, (5, 5), strides=(2, 2), padding='same', use_bias=False))
    assert model.output_shape == (None, 14, 14, 64)
    model.add(layers.BatchNormalization())
    model.add(layers.LeakyReLU())

    #Layer4
    model.add(layers.Conv2DTranspose(1, (5, 5), strides=(2, 2), padding='same', use_bias=False, activation='tanh'))
    assert model.output_shape == (None, 28, 28, 1)

    return model

"""Use the (as yet untrained) generator to create an image."""

generator = make_generator_model()

noise = tf.random.normal([1, 100])
generated_image = generator(noise, training=False)

plt.imshow(generated_image[0, :, :, 0], cmap='gray')

"""### The Discriminator
The discriminator is a CNN-based image classifier.
"""

def make_discriminator_model():
    model = tf.keras.Sequential()
    # Layer 1: use layers.Conv2D with 5x5 kernels and appropriate stride
    model.add(layers.Conv2D(64, (5, 5), strides=(2, 2), padding='same',
                                     input_shape=[28, 28, 1]))
    model.add(layers.LeakyReLU())# Activation function
    model.add(layers.Dropout(0.3))# Dropout
    # Layer 2: Conv2D
    model.add(layers.Conv2D(128, (5, 5), strides=(2, 2), padding='same'))
    model.add(layers.LeakyReLU())# Activation function
    model.add(layers.Dropout(0.3)) # Dropout
    # Layer 3: Fully connected layer, output dimension must be 1
    model.add(layers.Flatten())
    model.add(layers.Dense(1))
    return model

"""Use the (as yet untrained) discriminator to classify the generated images as real or fake.
The model will be trained to output positive values for real images, and negative values for fake images."""


discriminator = make_discriminator_model()
decision = discriminator(generated_image)
print (decision)


"""## Define the loss and optimizers
Define loss functions and optimizers for both models.
"""

# This method returns a helper function to compute the binary cross entropy loss

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

"""### Discriminator loss
Define the discriminator loss function: compare the discriminator's predictions on real images to an array of 1s.
"""

def discriminator_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output), real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output), fake_output)
    total_loss = real_loss + fake_loss
    return total_loss

"""### Generator loss
The generator's loss quantifies how well it was able to trick the discriminator. 
Intuitively, if the generator is performing well, the discriminator will classify the fake images as real (or 1). 
Again, use the same principle used to define the real_loss to define the generator_loss.
"""

def generator_loss(fake_output):
    generator_loss = cross_entropy(tf.ones_like(fake_output), fake_output)
    return generator_loss

"""The discriminator and the generator optimizers are different since both networks are trained separately. """

generator_optimizer = tf.keras.optimizers.Adam(1e-4) #learning rate of 1e-4
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

"""### Save checkpoints
This notebook also demonstrates how to save and restore models, which can be helpful in case a long running training task is interrupted (especially for larger datasets).
"""

checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,
                                 discriminator_optimizer=discriminator_optimizer,
                                 generator=generator,
                                 discriminator=discriminator)

"""## Define the training loop"""

EPOCHS = 50
noise_dim = 100
num_examples_to_generate = 16 # For visualization

# We will reuse this noise_vector overtime (so it's easier)
# to visualize progress in the animated GIF)
noise_vector = tf.random.normal([num_examples_to_generate, noise_dim])

"""The training loop should begin with generator receiving a random vector as input. That vector will be used to produce an image. The discriminator should then be used to classify real images (drawn from the training set) and fakes images (produced by the generator). The loss will be calculated for each of these models, and the gradients used to update the generator and discriminator"""

# Notice the use of `tf.function`
# This annotation causes the function to be "compiled".
@tf.function
def train_step(images):
    noise = tf.random.normal([BATCH_SIZE, noise_dim])

    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
      # Generator output
      generated_images = generator(noise, training=True)

      # Discriminator output
      real_output = discriminator(images, training=True)
      fake_output = discriminator(generated_images, training=True)

      # Loss functions
      gen_loss = generator_loss(fake_output)
      disc_loss = discriminator_loss(real_output, fake_output)

    # Gradients
    gradients_of_generator = gen_tape.gradient(gen_loss, generator.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, discriminator.trainable_variables)
    
    # Update both networks
    generator_optimizer.apply_gradients(zip(gradients_of_generator, generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, discriminator.trainable_variables))

def train(dataset, epochs):
  for epoch in range(epochs):
    start = time.time()

    for image_batch in dataset:
      train_step(image_batch)

    # Produce images for the GIF as we go
    display.clear_output(wait=True)
    generate_and_save_images(generator,
                             epoch + 1,
                             noise_vector)

    # Save the model every 15 epochs
    if (epoch + 1) % 15 == 0:
      checkpoint.save(file_prefix = checkpoint_prefix)

    print ('Time for epoch {} is {} sec'.format(epoch + 1, time.time()-start))

  # Generate after the final epoch
  display.clear_output(wait=True)
  generate_and_save_images(generator,
                           epochs,
                           noise_vector)

"""**Generate and save images**"""

def generate_and_save_images(model, epoch, test_input):
  # Notice `training` is set to False.
  # This is so all layers run in inference mode (batchnorm).
  predictions = model(test_input, training=False)

  fig = plt.figure(figsize=(4,4))

  for i in range(predictions.shape[0]):
      plt.subplot(4, 4, i+1)
      plt.imshow(predictions[i, :, :, 0] * 127.5 + 127.5, cmap='gray')
      plt.axis('off')

  plt.savefig('image_at_epoch_{:04d}.png'.format(epoch))
  plt.show()

"""## Train the model
Call the `train()` method defined above to train the generator and discriminator simultaneously. 
Note, training GANs can be tricky. It's important that the generator and discriminator do not overpower each other (e.g., that they train at a similar rate).
At the beginning of the training, the generated images look like random noise. As training progresses, the generated digits will look increasingly real.
After about 50 epochs, they resemble MNIST digits. This may take about one minute / epoch with the default settings on Colab.
"""

# Commented out IPython magic to ensure Python compatibility.
# %%time
# train(train_dataset, EPOCHS)

"""Restore the latest checkpoint."""

checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

"""## Create a GIF"""

# Display a single image using the epoch number
def display_image(epoch_no):
  return PIL.Image.open('image_at_epoch_{:04d}.png'.format(epoch_no))

display_image(EPOCHS)

"""Use imageio to create an animated gif using the images saved during training."""

anim_file = 'dcgan.gif'

with imageio.get_writer(anim_file, mode='I') as writer:
  filenames = glob.glob('image*.png')
  filenames = sorted(filenames)
  last = -1
  for i,filename in enumerate(filenames):
    frame = 8*(i**0.25)
    if round(frame) > round(last):
      last = frame
    else:
      continue
    image = imageio.imread(filename)
    writer.append_data(image)
  image = imageio.imread(filename)
  writer.append_data(image)

import IPython
if IPython.version_info > (6,2,0,''):
  display.Image(filename=anim_file)

"""If you're working in Colab you can download the animation with the code below:"""

try:
  from google.colab import files
except ImportError:
  pass
else:
  files.download(anim_file)
