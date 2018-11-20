from operator import mul
from functools import reduce

import tensorflow as tf
import numpy as np

from typing import Tuple

from .Policy import Policy
from tensorflow.keras import Model
from tensorflow.keras.layers import Reshape
from rinokeras.common.layers import Stack, DenseStack
from rinokeras.common.distributions import CategoricalPd, DiagGaussianPd


class StandardPolicy(Model):

    def __init__(self,
                 action_shape: Tuple[int, ...],
                 action_space: str,
                 embedding_model: Model,
                 model_dim: int = 64,
                 n_layers_logits: int = 1,
                 n_layers_value: int = 1,
                 take_greedy_actions: bool = False,
                 initial_logstd: float = 0,
                 **kwargs) -> None:

        super().__init__(**kwargs)
        if not isinstance(action_shape, (tuple, list)):
            raise TypeError("Expected tuple or list for action shape, received {}".format(type(action_shape)))
        if action_space not in ['discrete', 'continuous']:
            raise ValueError("action_space must be one of <discrete, continuous>, received {}".format(action_space))

        self.action_shape = action_shape
        self.model_dim = model_dim
        self.n_layers_logits = n_layers_logits
        self.n_layers_value = n_layers_value

        self.embedding_model = embedding_model
        self.logits_function = self._setup_logits_function()
        self.value_function = self._setup_value_function()
        self.action_distribution = CategoricalPd(name='action') if action_space == 'discrete' \
            else DiagGaussianPd(initial_logstd=initial_logstd, name='action')

        self._take_greedy_actions = take_greedy_actions
        self._initial_logstd = initial_logstd

    def _setup_logits_function(self, activation=None):
        ac_dim = reduce(mul, self.action_shape)

        logits_function = Stack(name='logits')
        logits_function.add(
            DenseStack(self.n_layers_logits * [self.model_dim] + [ac_dim], output_activation=activation))
        logits_function.add(Reshape(self.action_shape))
        return logits_function

    def _setup_value_function(self):
        value_function = DenseStack(self.n_layers_value * [self.model_dim] + [1], output_activation=None)
        return value_function

    def call(self, obs, is_training=False):
        self._obs = obs

        embedding = self.embedding_model(obs)
        logits = self.logits_function(embedding)

        value = self.value_function(embedding)
        action = self.action_distribution(logits, greedy=self._take_greedy_actions)

        self._action = action
        self._value = value

        if is_training:
            return logits, value
        else:
            return action

    def predict(self, obs):
        if not self.built:
            raise RuntimeError("Policy is not built, please call the policy before running predict.")
        if tf.executing_eagerly():
            return self.call(obs, is_training=False).numpy()
        else:
            sess = self._get_session()
            return sess.run(self._action, feed_dict={self._obs: obs})

    def logp_actions(self, logits, actions):
        return self.action_distribution.logp_actions(logits, actions)

    def entropy(self, logits):
        return self.action_distribution.entropy(logits)

    def _get_session(self):
        sess = tf.get_default_session()
        if sess is None:
            raise RuntimeError("This method must be run inside a tf.Session context")
        return sess
