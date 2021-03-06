import numpy as np
import tensorflow as tf
import tensornets as nets
import tensorflow_hub as hub

models_list = [
    (nets.MobileNet35v2, (224, 224, 3), 'mobilenet_v2_035_224'),
    (nets.MobileNet50v2, (224, 224, 3), 'mobilenet_v2_050_224'),
    (nets.MobileNet75v2, (224, 224, 3), 'mobilenet_v2_075_224'),
    (nets.MobileNet100v2, (224, 224, 3), 'mobilenet_v2_100_224'),
    (nets.MobileNet130v2, (224, 224, 3), 'mobilenet_v2_130_224'),
    (nets.MobileNet140v2, (224, 224, 3), 'mobilenet_v2_140_224'),
    (nets.PNASNetlarge, (331, 331, 3), 'pnasnet_large'),
]

url = 'https://tfhub.dev/google/imagenet'


for (net, shape, model_name) in models_list:

    with tf.Graph().as_default():

        inputs = tf.placeholder(tf.float32, [None] + list(shape))
        model = net(inputs, scope='a')

        tfhub = hub.Module("%s/%s/classification/1" % (url, model_name))
        features = tfhub(inputs, signature="image_classification",
                         as_dict=True)
        model_tfhub = tf.nn.softmax(features['default'])

        img = nets.utils.load_img('cat.png',
                                  target_size=int(shape[0] * 8 / 7),
                                  crop_size=shape[0])

        with tf.Session() as sess:

            # Retrieve values
            sess.run(tf.global_variables_initializer())
            weights = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES,
                                        scope='module')
            values = sess.run(weights)
            for i in range(-2, 0):
                values[i] = np.delete(np.squeeze(values[i]), 0, axis=-1)

            # Adjust the order of the values to cover TF < 1.4.0
            names = [w.name[2:] for w in model.get_weights()]
            for i in range(len(names) - 1):
                if 'gamma:0' in names[i] and 'beta:0' in names[i + 1]:
                    names[i], names[i + 1] = names[i + 1], names[i]
                    values[i], values[i + 1] = values[i + 1], values[i]

            # Save the values as the TensorNets format
            np.savez(model_name, names=names, values=values)

            # Load and set the values
            weights = model.get_weights()
            values = nets.utils.parse_weights(model_name + '.npz')
            sess.run([w.assign(v) for (w, v) in zip(weights, values)])

            # Run equivalence tests
            preds = sess.run(model, {inputs: model.preprocess(img)})
            preds_tfhub = sess.run(model_tfhub, {inputs: img / 255.})
            np.testing.assert_allclose(preds, preds_tfhub[:, 1:], atol=1e-4)
