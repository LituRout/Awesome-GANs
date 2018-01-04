from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

from tensorflow.examples.tutorials.mnist import input_data

import sys
import time

import wgan_model as wgan

sys.path.append('../')
import image_utils as iu

results = {
    'output': './gen_img/',
    'checkpoint': './model/checkpoint',
    'model': './model/WGAN-model.ckpt'
}

train_step = {
    'global_step': 250001,
    'logging_interval': 2500,
}


def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset load
    mnist = input_data.read_data_sets('./MNIST_data', one_hot=True)

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # WGAN Model
        model = wgan.WGAN(s,
                          enable_bn=True,
                          enable_adam=True,
                          enable_gp=True)  # Improved-WGAN with gradient penalty

        # Initializing
        s.run(tf.global_variables_initializer())

        sample_x, _ = mnist.train.next_batch(model.sample_num)
        sample_x = sample_x.reshape([-1] + model.image_shape)  # (-1, 28, 28, 1)

        sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)

        for step in range(train_step['global_step']):
            # Update critic
            model.critic = 5
            if step % 500 == 0 or step < 25:
                model.critic = 100
            if model.EnableGP:
                model.critic = 1

            for _ in range(model.critic):
                batch_x, _ = mnist.train.next_batch(model.batch_size)  # with batch_size, 64
                batch_x = batch_x.reshape([-1] + model.image_shape)  # (-1, 28, 28, 1)

                batch_z = np.random.uniform(-1., 1.,  # range -1 ~ 1
                                            size=[model.batch_size, model.z_dim]).astype(np.float32)

                # Update d_clip
                if not model.EnableGP:
                    s.run(model.d_clip)

                # Update D network
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.z: batch_z
                                  })

            # Generate z
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x: batch_x,
                                  model.z: batch_z,
                              })

            # Logging
            if step % train_step['logging_interval'] == 0:
                batch_x, _ = mnist.test.next_batch(model.batch_size)
                batch_x = batch_x.reshape([-1] + model.image_shape)  # (-1, 28, 28, 1)

                batch_z = np.random.uniform(-1., 1.,  # range -1. ~ 1.
                                            [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x: batch_x,
                                                    model.z: batch_z,
                                                })

                # Print loss
                print("[+] Step %08d => " % step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                samples = s.run(model.g,
                                feed_dict={
                                    model.x: sample_x,
                                    model.z: sample_z,
                                })

                # Summary saver
                model.writer.add_summary(summary, step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_{:08d}.png'.format(step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir)

                # Model save
                model.saver.save(s, results['model'], global_step=step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))  # took over 2hrs for 10k steps on my machine

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
