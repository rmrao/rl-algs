"""
Various utility functions that are commonly used in our models and during training.
"""

import tensorflow as tf


def convert_padding_mask_to_attention_mask(sequence, padding_mask):
    """Given a padded input tensor of sequences and a boolean mask for each position
    in the sequence, returns a 3D boolean mask for use in attention.
    
    Args:
        sequence (tf.Tensor): Tensor of shape [batch_size, sequence_length_1, ndim]
        padding_mask (tf.Tensor[bool]): Tensor of shape [batch_size, sequence_length_2]
    
    Returns:
        tf.Tensor[bool]: Tensor of shape [batch_size, sequence_length_1, sequence_length_2]
    """
    batch_assert = tf.assert_equal(tf.shape(padding_mask)[0], tf.shape(sequence)[0],
                                   message='batch size mismatch between input sequence and  \
                                            padding_mask')
    rank_assert = tf.assert_equal(tf.rank(padding_mask), 2,
                                  message='Can only convert 2D position mask to 3D attention mask')

    with tf.control_dependencies([batch_assert, rank_assert]):
        attention_mask = tf.tile(padding_mask[:, None, :], (1, tf.shape(sequence)[1], 1))
        return attention_mask


def convert_sequence_length_to_sequence_mask(sequence, sequence_lengths):
    """Given a padded input tensor of sequences and a tensor of lengths, returns
    a boolean mask for each position in the sequence indicating whether or not
    that position is padding.
    
    Args:
        sequence (tf.Tensor): Tensor of shape [batch_size, sequence_length, ndim]
        sequence_lengths (tf.Tensor[int]): Tensor of shape [batch_size]
    
    Returns:
        tf.Tensor[bool]: Tensor of shape [batch_size, sequence_length]
    """
    batch_assert = tf.assert_equal(tf.shape(sequence_lengths)[0], tf.shape(sequence)[0],
                                   message='batch size mismatch between input sequence and  \
                                            sequence_lengths')
    rank_assert = tf.assert_equal(tf.rank(sequence_lengths), 1,
                                  message='Can only convert 1D sequence_lengths to 2D mask')

    with tf.control_depencencies([batch_assert, rank_assert]):
        indices = tf.tile(tf.range(tf.shape(sequence)[1])[None, :], (tf.shape(sequence_lengths)[0], 1))
        mask = indices < sequence_lengths[:, None]
        return mask