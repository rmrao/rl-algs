from functools import reduce
from operator import mul

import tensorflow as tf
from tensorflow.contrib import slim, rnn
import numpy as np

from .StandardPolicy import StandardPolicy

class LSTMPolicy(StandardPolicy):

    def __init__(self, obs_shape, 
                        ac_shape, 
                        discrete, 
                        scope='agent', 
                        obs_dtype=tf.float32,
                        action_method='greedy',
                        use_conv=False,
                        embedding_architecture=[(64,), (64,)],
                        logit_architecture=[(64,), (64,)],
                        value_architecture=[(64,), (64,)],
                        lstm_cell_size=512,
                        use_reward=False):
        self._lstm_cell_size = lstm_cell_size
        self._use_reward = use_reward
        super().__init__(obs_shape, ac_shape, discrete, scope, obs_dtype, action_method, use_conv,
                            embedding_architecture, logit_architecture, value_architecture)

    def _setup_placeholders(self):
        self.sy_obs = tf.placeholder(self._obs_dtype, (None, None) + self._obs_shape, name='obs_placeholder')
        if self._use_reward:
            self.sy_rew = tf.placeholder(tf.float32, (None,), name='rew_placeholder')
    
    def _setup_agent(self):
        obs_placeholder = self.sy_obs
        batch_size = tf.shape(self.sy_obs)[0]
        num_timesteps = tf.shape(self.sy_obs)[1]
        self.sy_obs = tf.reshape(self.sy_obs, (batch_size * num_timesteps,) + self._obs_shape)
        self._setup_embedding_network()
        self.sy_obs = obs_placeholder
        if self._use_reward:
            rew = tf.expand_dims(self.sy_rew, 1)
            self._embedding = tf.concat((self._embedding, rew), 1)

        self._embedding = tf.reshape(self._embedding, (batch_size, num_timesteps, self._embedding.shape[1]))
        self._setup_lstm_network()

        self._setup_action_logits()
        self._setup_value_function()

    def _setup_lstm_network(self, reuse=False):
        with tf.variable_scope('lstm', reuse=reuse):
            lstm = rnn.BasicLSTMCell(self._lstm_cell_size)
            self._state_size = lstm.state_size

            c_init = np.zeros((1, lstm.state_size.c), np.float32)
            h_init = np.zeros((1, lstm.state_size.h), np.float32)
            self._state_init = (c_init, h_init)
            self._state_curr = self._state_init
            c_in = tf.placeholder(tf.float32, [None, lstm.state_size.c], name='c_in')
            h_in = tf.placeholder(tf.float32, [None, lstm.state_size.h], name='h_in')
            self._state_in = (c_in, h_in)

            state_in = rnn.LSTMStateTuple(c_in, h_in)
            lstm_outputs, lstm_state = tf.nn.dynamic_rnn(lstm, self._embedding, initial_state=state_in, dtype=tf.float32)

            lstm_c, lstm_h = lstm_state
            self._embedding = tf.reshape(lstm_outputs, [-1, self._lstm_cell_size])
            self._layers.append(self._embedding)

            # All this stuff is only needed when collecting rollouts, so can hardcode [0, :]
            self._state_out = [lstm_c[:1,:], lstm_h[:1,:]] # doing it like this does keepdims automatically I think

    def predict(self, obs, rew=None, return_activations=False):
        if obs.ndim == 2 and obs.shape[0] == 1:
            obs = np.expand_dims(obs, 1) # add time dimension
        sess = self._get_session()
        to_return = [self._action, self._state_out[0], self._state_out[1]]
        if return_activations:
            to_return.append(self._layers)
        feed_dict = {self.sy_obs : obs,
                        self._state_in[0] : self._state_curr[0],
                        self._state_in[1] : self._state_curr[1]}
        if self._use_reward:
            if np.isscalar(rew):
                rew = np.array([rew])
            feed_dict[self.sy_rew] = rew
        to_return = sess.run(to_return, feed_dict=feed_dict)
        self._state_curr = to_return[1:3]
        return to_return[0] if not return_activations else to_return

    def clear_memory(self):
        self._state_curr = self._state_init

    # Ideally, a training algorithm should be policy agnostic. However, some policies, like the LSTMPolicy,
    # require extra goodies like an input state. It's easy to handle this when interacting with the environment,
    # because it calls the policy's "predict" method, but the training algorithm can't really do that. It 
    # needs to pass a value in for these extra variables. So we can define a property "feed dict extras"
    # that returns any extra information the policy needs that is stored with the policy on device
    # rather than on host.
    def feed_dict_extras(self, batch):
        batch_size = batch['obs'].shape[0]
        extras = {
                self._state_in[0] : np.tile(self._state_init[0], (batch_size, 1)),
                self._state_in[1] : np.tile(self._state_init[1], (batch_size, 1))
        }
        if self._use_reward:
            extras[self.sy_rew] = batch['rew']
        return extras
    
    def make_copy(self, scope):
        return LSTMPolicy(self._obs_shape,
                                self._ac_shape,
                                self._discrete,
                                scope,
                                self._obs_dtype,
                                self._action_method,
                                self._use_conv,
                                self._embedding_architecture,
                                self._logit_architecture,
                                self._value_architecture,
                                self._lstm_cell_size)






        
