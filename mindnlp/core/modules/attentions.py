# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""attention module"""
from typing import Optional

import mindspore
import mindspore.numpy as mnp
from mindspore import Parameter, ops, nn
from mindspore.common.initializer import initializer, Uniform
from mindnlp._legacy.nn import Dropout

class ScaledDotAttention(nn.Module):
    r"""
    Scaled Dot-Product Attention
    Scaled Dot-Product Attention proposed in "Attention Is All You Need"

    .. math::

        Attention(Q,K,V)=softmax(\frac{QK^T}{\sqrt{d_k}})V

    Args:
        dropout (float): The keep rate, greater than 0 and less equal than 1.
            E.g. rate=0.9, dropping out 10% of input units. Default: 0.9.

    Examples:
        >>> import mindspore
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import ScaledDotAttention
        >>> model = ScaledDotAttention(dropout=0.9)
        >>> q = Tensor(np.ones((2, 32, 512)), mindspore.float32)
        >>> k = Tensor(np.ones((2, 20, 512)), mindspore.float32)
        >>> v = Tensor(np.ones((2, 20, 400)), mindspore.float32)
        >>> output, att = model(q, k, v)
        >>> print(output.shape)
        # (2, 1024, 512)
        >>> print(att.shape)
        # (2, 1024, 32)
    """
    def __init__(self, dropout=0.9):
        r"""
        Initializes an instance of the ScaledDotAttention class.
        
        Args:
            self: The instance of the ScaledDotAttention class.
            dropout (float, optional): The probability of an element to be zeroed in the dropout layer. 
                Default is 0.9. Must be a value between 0 and 1.
        
        Returns:
            None
        
        Raises:
            None
        """
        super().__init__()
        self.softmax = nn.Softmax(axis=-1)
        self.dropout = Dropout(p=dropout)

    def forward(self, query, key, value, mask: Optional[mindspore.Tensor] = None):
        """Scaled dot-product attention network forwardion.

        Args:
            query (mindspore.Tensor): The query vector.
                [batch_size, query_size, hidden_size]
            key (mindspore.Tensor): The key vector.
                [batch_size, key_size, hidden_size]
            value (mindspore.Tensor): The value vector.
                [batch_size, seq_len, value_hidden_size]
            mask Optional[mindspore.Tensor[bool]]: The mask vector.
                [batch_size, query_size, key_size]

        Returns:
            - **output** (mindspore.Tensor) - The output of linear attention.
              [batch_size, query_size, value_hidden_size]
            - **attn** (mindspore.Tensor) - The last layer of attention weights.
              [batch_size, query_size, key_size]
        """
        scale = mnp.sqrt(ops.scalar_to_tensor(query.shape[-1]))
        scores = ops.matmul(query, key.swapaxes(-1, -2)) / scale
        if mask is not None:
            scores = ops.masked_fill(scores, mask == 0, -1e9)
        attn = self.softmax(scores)
        attn = self.dropout(attn)
        output = ops.matmul(attn, value)
        return output, attn

class AdditiveAttention(nn.Module):
    r"""
    Additive Attention
    Additive Attention proposed in "Neural Machine Translation by Jointly Learning to Align and Translate" paper

    .. math::

        Attention(Q,K,V) = (W_v)T *(tanh(W_q * Q + W_k * K))

    Args:
        hidden_dims (int): The dimesion of hidden state vector
        dropout (float): The keep rate, greater than 0 and less equal than 1.
            E.g. rate=0.9, dropping out 10% of input units. Default: 0.9.

    Examples:
        >>> import mindspore
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import AdditiveAttention
        >>> model = AdditiveAttention(hidden_dims=512, dropout=0.9)
        >>> q = Tensor(np.ones((2, 32, 512)), mindspore.float32)
        >>> k = Tensor(np.ones((2, 20, 512)), mindspore.float32)
        >>> v = Tensor(np.ones((2, 20, 512)), mindspore.float32)
        >>> mask_shape = (2, 32, 20)
        >>> mask = Tensor(np.ones(mask_shape), mindspore.bool_)
        >>> output, attn = model(q, k, v, mask)
        >>> print(output.shape, attn.shape)
        (2, 32, 512) (2, 32, 20)
    """
    def __init__(self, hidden_dims, dropout=0.9):
        r"""
        Args:
            self (object): The instance of the class AdditiveAttention.
            hidden_dims (int): The dimensionality of the hidden representations.
            dropout (float, optional): The dropout probability for regularization. Default is 0.9.
        
        Returns:
            None: This method does not return any value.
        
        Raises:
            ValueError: If the value of hidden_dims is not a positive integer.
            ValueError: If the value of dropout is not within the range [0, 1].
            TypeError: If the input types are not as expected.
        """
        super().__init__()
        self.w_q = nn.Linear(hidden_dims, hidden_dims, bias=False)
        self.w_k = nn.Linear(hidden_dims, hidden_dims, bias=False)
        self.w_output = nn.Linear(hidden_dims, 1, bias=True)
        self.dropout = Dropout(p=dropout)
        self.tanh = nn.Tanh()
        # Set bias parameter
        bias_layer = initializer(Uniform(scale=0.1), [hidden_dims], mindspore.float32)
        self.bias = Parameter(bias_layer)
        self.softmax = nn.Softmax(axis=-1)

    def forward(self, query, key, value, mask: Optional[mindspore.Tensor] = None):
        """Additive attention network forwardion.

        Args:
            query (mindspore.Tensor): The query vector.
                [batch_size, query_size, hidden_size]
            key (mindspore.Tensor): The key vector.
                [batch_size, key_size, hidden_size]
            value (mindspore.Tensor): The value vector.
                [batch_size, seq_len, value_hidden_size]
            mask Optional[mindspore.Tensor[bool]]: The mask vector.
                [batch_size, query_size, key_size]

        Returns:
            - **output** (mindspore.Tensor) - The output of linear attention.
              [batch_size, query_size, value_hidden_size]
            - **attn** (mindspore.Tensor) - The last layer of attention weights.
              [batch_size, query_size, key_size]
        """
        query = self.w_q(query)
        key = self.w_k(key)
        features = query.expand_dims(-2) + key.expand_dims(-3) + self.bias
        scores = self.w_output(self.tanh(features)).squeeze(-1)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        attn = self.softmax(scores)
        attn = self.dropout(attn)
        output = ops.matmul(attn, value)
        return output, attn

class LinearAttention(nn.Module):
    r"""
    Linear attention computes attention by concat the query and key vector.

    Args:
        query_size (int): The sentence length of `query`. Usually query.shape[-2]
        key_size (int): The sentence length of `key`. Usually key.shape[-2]
        hidden_dim (int): The dimension of hidden vector
        dropout (float): The keep rate, greater than 0 and less equal than 1.
            Default: 0.9.

    Examples:
        >>> import mindspore
        >>> import mindspore.numpy as np
        >>> from mindspore import ops
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import LinearAttention
        >>> standard_normal = ops.StandardNormal(seed=0)
        >>> query = standard_normal((2, 32, 512))
        >>> key = standard_normal((2, 20, 512))
        >>> value = standard_normal((2, 20, 500))
        >>> net = LinearAttention(batch_size=2, query_dim=32, key_dim=20, hidden_dim=512)
        >>> mask_shape = (2, 32, 20)
        >>> mask = Tensor(np.ones(mask_shape), mindspore.bool_)
        >>> output, attn = net(query, key, value, mask)
        >>> print(output.shape, attn.shape)
        (2, 32, 512) (2, 32, 20)
    """
    def __init__(self, query_dim, key_dim, hidden_dim, dropout=0.9):
        r"""
        Initializes an instance of the LinearAttention class.
        
        Args:
            self: The instance of the LinearAttention class.
            query_dim (int): The dimension of the query input.
            key_dim (int): The dimension of the key input.
            hidden_dim (int): The dimension of the hidden layer.
            dropout (float): The dropout rate for regularization. Default is 0.9.
        
        Returns:
            None. This method initializes the LinearAttention instance with the specified parameters.
        
        Raises:
            None.
        """
        super().__init__()
        self.w_linear = nn.Linear(query_dim + key_dim, query_dim, bias=False)
        self.softmax = nn.Softmax(axis=-1)
        self.tanh = nn.Tanh()
        self.v_linear = nn.Linear(hidden_dim, key_dim, bias=False)
        self.dropout = Dropout(p=dropout)
        #set bias parameter
        uniformreal = ops.UniformReal(seed=0)
        bias_layer = uniformreal((hidden_dim,))
        self.bias = Parameter(bias_layer)

    def forward(self, query, key, value, mask: Optional[mindspore.Tensor] = None):
        """linear attention with concatenate forwardion

        Args:
            query (mindspore.Tensor): The query vector.
                [batch_size, query_size, hidden_size]
            key (mindspore.Tensor): The key vector.
                [batch_size, key_size, hidden_size]
            value (mindspore.Tensor): The value vector.
                [batch_size, seq_len, value_hidden_size]
            mask Optional[mindspore.Tensor[bool]]: The mask vector.
                [batch_size, query_size, key_size]

        Returns:
            - **output** (mindspore.Tensor) - The output of linear attention.
              [batch_size, query_size, value_hidden_size]
            - **attn** (mindspore.Tensor) - The last layer of attention weights.
              [batch_size, query_size, key_size]
        """
        features = self.w_linear(ops.concat((query, key), -2).swapaxes(-1, -2)).swapaxes(-1, -2)
        scores = self.v_linear(self.tanh(features + self.bias))

        if mask is not None:
            scores = ops.masked_fill(scores, mask == 0, -1e9)
        attn = self.softmax(scores)
        attn = self.dropout(attn)
        output = ops.matmul(attn, value)
        return output, attn

class CosineAttention(nn.Module):
    r"""
    Cosine Attention
    Cosine Attention proposed in "Neural Turing Machines" paper

    .. math::

          Sim(Q, K) = (Q * (K)T) / |Q| * |K|
          Attention(Q,K,V) = softmax(Sim(Q, K)) * V


    Args:
        dropout (float): The keep rate, greater than 0 and less equal than 1.
            E.g. rate=0.9, dropping out 10% of input units. Default: 0.9.

    Examples:
        >>> import mindspore
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import CosineAttention
        >>> model = CosineAttention(dropout=0.9)
        >>> q = Tensor(np.ones((2, 32, 512)), mindspore.float32)
        >>> k = Tensor(np.ones((2, 20, 512)), mindspore.float32)
        >>> v = Tensor(np.ones((2, 20, 512)), mindspore.float32)
        >>> mask_shape = (2, 32, 20)
        >>> mask = Tensor(np.ones(mask_shape), mindspore.bool_)
        >>> output, attn = model(q, k, v, mask)
        >>> print(output.shape, attn.shape)
        (2, 32, 512) (2, 32, 20)
    """
    def __init__(self, dropout=0.9):
        r"""
        Initializes an instance of the CosineAttention class.
        
        Args:
            self: The instance of the CosineAttention class.
            dropout (float, optional): The dropout probability for the attention mechanism. 
                It controls the probability of elements being zeroed out during training. 
                The value should be in the range [0.0, 1.0]. Default is 0.9.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            ValueError: If the value of dropout is outside the range [0.0, 1.0].
        """
        super().__init__()
        self.softmax = nn.Softmax(axis=-1)
        self.dropout = Dropout(p=dropout)

    def forward(self, query, key, value, mask: Optional[mindspore.Tensor] = None):
        """Consine attention network forwardion.

        Args:
            query (mindspore.Tensor): The query vector.
                [batch_size, query_size, hidden_size]
            key (mindspore.Tensor): The key vector.
                [batch_size, key_size, hidden_size]
            value (mindspore.Tensor): The value vector.
                [batch_size, seq_len, value_hidden_size]
            mask Optional[mindspore.Tensor[bool]]: The mask vector.
                [batch_size, query_size, key_size]

        Returns:
            - **output** (mindspore.Tensor) - The output of linear attention.
              [batch_size, query_size, value_hidden_size]
            - **attn** (mindspore.Tensor) - The last layer of attention weights.
              [batch_size, query_size, key_size]
        """
        query_length = ops.sqrt((query * query).sum())
        key_length = ops.sqrt((key * key).sum())
        features = ops.matmul(query, key.swapaxes(-1, -2))
        scores = ops.div(features, (query_length * key_length))
        if mask is not None:
            scores = ops.masked_fill(scores, mask == 0, -1e9)
        attn = self.softmax(scores)
        scores = self.dropout(attn)
        output = ops.matmul(attn, value)
        return output, attn

def _masked_softmax(tensor, mask):
    """
    Calculate the softmax weight of tensor under mask.
    """
    softmax = ops.Softmax(axis=-1)
    tensor_shape = tensor.shape
    reshaped_tensor = tensor.view(-1, tensor_shape[-1])
    while mask.ndim < tensor.ndim:
        mask = ops.expand_dims(mask, 1)
    mask = mask.expand_as(tensor)
    reshaped_mask = mask.view(-1, mask.shape[-1])
    result = softmax(reshaped_tensor * reshaped_mask)
    result = result * reshaped_tensor
    # Avoid the divisions by zeros case
    result = result / (result.sum(axis=-1, keepdims=True) + 1e-13)
    return result.view(tensor_shape)

def _weighted_sum(tensor, weights, mask):
    """
    Calculate the weighted sum of tensor and weight under mask.
    """
    batmatmul = ops.BatchMatMul()
    w_sum = batmatmul(weights, tensor)
    while mask.ndim < tensor.ndim:
        mask = ops.expand_dims(mask, 1)
    mask = ops.transpose(mask, (0, -1, -2))
    mask = mask.expand_as(w_sum)
    return w_sum * mask

class BinaryAttention(nn.Module):
    r"""
    Binary Attention, For a given sequence of two vectors :
    x_i and y_j, the BiAttention module will
    compute the attention result by the following equation:

    .. math::

          \begin{array}{ll} \\
            e_{ij} = {x}^{\mathrm{T}}_{i}{y}_{j} \\
            {\hat{x}}_{i} = \sum_{j=1}^{\mathcal{l}_{y}}{\frac{
                \mathrm{exp}(e_{ij})}{\sum_{k=1}^{\mathcal{l}_{y}}{\mathrm{exp}(e_{ik})}}}{y}_{j} \\
            {\hat{y}}_{j} = \sum_{i=1}^{\mathcal{l}_{x}}{\frac{
                \mathrm{exp}(e_{ij})}{\sum_{k=1}^{\mathcal{l}_{x}}{\mathrm{exp}(e_{ik})}}}{x}_{i} \\
        \end{array}

    Examples:
        >>> import mindspore
        >>> import mindspore.numpy as np
        >>> from mindspore import ops
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import BinaryAttention
        >>> model = BinaryAttention()
        >>> standard_normal = ops.StandardNormal(seed=0)
        >>> x = standard_normal((2, 30, 512))
        >>> y = standard_normal((2, 20, 512))
        >>> x_mask = Tensor(np.zeros_like(x.shape[:-1]), mindspore.float32)
        >>> y_mask = Tensor(np.zeros_like(y.shape[:-1]), mindspore.float32)
        >>> output_x, output_y = model(x, x_mask, y, y_mask)
        >>> print(output_x.shape, output_y.shape)
        (2, 30, 512) (2, 20, 512)
    """
    def __init__(self):
        r"""
        Initializes an instance of the BinaryAttention class.
        
        Args:
            self: The instance of the BinaryAttention class being initialized.
        
        Returns:
            None. This method does not return any value.
        
        Raises:
            No specific exceptions are raised within this method.
        """
        super().__init__()
        self.bmm = ops.BatchMatMul()

    def forward(self, x_batch, x_mask, y_batch, y_mask):
        """Compute the attention result

        Args:
            x_batch (mindspore.Tensor): [batch_size, x_seq_len, hidden_size]
            x_mask (mindspore.Tensor): [batch_size, x_seq_len]
            y_batch (mindspore.Tensor): [batch_size, y_seq_len, hidden_size]
            y_mask (mindspore.Tensor): [batch_size, y_seq_len]

        Returns:
            - **attended_x** (mindspore.Tensor) - The output of the attention_x.
            - **attended_y** (mindspore.Tensor) - The output of the attention_y.
        """
        similarity_matrix = self.bmm(x_batch, ops.transpose(y_batch, (0, 2, 1)))
        x_y_attn = _masked_softmax(similarity_matrix, y_mask)
        y_x_attn = _masked_softmax(ops.transpose(similarity_matrix, (0, 2, 1)), x_mask)
        attended_x = _weighted_sum(y_batch, x_y_attn, x_mask)
        attended_y = _weighted_sum(x_batch, y_x_attn, y_mask)
        return attended_x, attended_y

class SelfAttention(nn.Module):
    r"""
    Self attention is from the paper “attention is all you need”

    Args:
        d_model (int): The `query`, `key` and `value` vectors dimensions.
            Default: 512.
        dropout (float): The keep rate, greater than 0 and less equal than 1.
            Default: 0.9.
        bias (bool): whether to use a bias vector. Default: True.
        attention_mode (str): attention mode. Default: "dot".

    Examples:
        >>> import mindspore
        >>> import mindspore.numpy as np
        >>> from mindspore import ops
        >>> from mindspore import Tensor
        >>> from mindspore.text.modules.attentions import SelfAttention
        >>> standard_normal = ops.StandardNormal(seed=0)
        >>> query = standard_normal((2, 32, 512))
        >>> key = standard_normal((2, 20, 512))
        >>> value = standard_normal((2, 20, 512))
        >>> mask_shape = (2, 32, 20)
        >>> mask = Tensor(np.ones(mask_shape), mindspore.bool_)
        >>> net = SelfAttention()
        >>> output, attn = net(query, key, value, mask)
        >>> print(x.shape, attn.shape)
        (2, 32, 512) (2, 32, 20)
    """
    def __init__(self, d_model=512, dropout_rate=0.1, bias=False, attention_mode="dot"):
        r"""
        Initializes a SelfAttention object.
        
        Args:
            self (SelfAttention): The instance of the SelfAttention class.
            d_model (int, optional): The dimensionality of the input and output vectors. Defaults to 512.
            dropout_rate (float, optional): The dropout rate to be applied. Defaults to 0.1.
            bias (bool, optional): Whether to include bias terms in linear transformations. Defaults to False.
            attention_mode (str, optional): The type of attention mechanism to be used. 
                Supported modes are 'dot', 'additive', and 'cosine'. Defaults to 'dot'.
        
        Returns:
            None.
        
        Raises:
            ValueError: If the attention_mode is not one of 'dot', 'additive', or 'cosine'.
        '''
        
        # Method code:
        def __init__(self, d_model=512, dropout_rate=0.1, bias=False, attention_mode='dot'):
            super().__init__()
            self.d_model = d_model
            self.linear_query = nn.Linear(d_model, d_model, bias=bias)
            self.linear_key = nn.Linear(d_model, d_model, bias=bias)
            self.linear_value = nn.Linear(d_model, d_model, bias=bias)
            self.linear_out = nn.Linear(d_model, d_model, bias=bias)
            if 'add' in attention_mode.lower():
                self.attention_mode = AdditiveAttention(hidden_dims=self.d_model, dropout=1 - dropout_rate)
            elif 'cos' in attention_mode.lower():
                self.attention_mode = CosineAttention(dropout=1 - dropout_rate)
            else:
                self.attention_mode = ScaledDotAttention(1 - dropout_rate)
        """
        super().__init__()
        self.d_model = d_model
        self.linear_query = nn.Linear(d_model, d_model, bias=bias)
        self.linear_key = nn.Linear(d_model, d_model, bias=bias)
        self.linear_value = nn.Linear(d_model, d_model, bias=bias)
        self.linear_out = nn.Linear(d_model, d_model, bias=bias)
        if "add" in attention_mode.lower():
            self.attention_mode = AdditiveAttention(hidden_dims=self.d_model, dropout=1-dropout_rate)
        elif "cos" in attention_mode.lower():
            self.attention_mode = CosineAttention(dropout=1-dropout_rate)
        else:
            self.attention_mode = ScaledDotAttention(1-dropout_rate)

    def forward(self, query, key, value, mask: Optional[mindspore.Tensor] = None):
        """Get self-attention output and attention weights.

        Args:
            query (mindspore.Tensor): The query vector.
            key (mindspore.Tensor): The key vector.
            value (mindspore.Tensor): The value vector.
                [batch_size, seq_len, d_model]
            mask Optional[mindspore.Tensor[bool]]: The mask vector.
                [batch_size, seq_len, seq_len]

        Returns:
            - **output** (mindspore.Tensor) - The output of self attention.
            - **attn** (mindspore.Tensor) - The last layer of attention weights
        """
        query = self.linear_query(query)
        key = self.linear_key(key)
        value = self.linear_value(value)
        output, self_attn = self.attention_mode(query, key, value, mask)
        return self.linear_out(output), self_attn

class LocationAwareAttention(nn.Module):
    r"""
    Location Aware Attention
    Location Aware Attention proposed in "Attention-Based Models for Speech Recognition"

    Args:
        hidden_dim (int): The dimension of the hidden states
        smoothing (bool): Smoothing label from "Attention-Based Models for Speech Recognition"

    Examples:
        >>> import mindspore
        >>> import mindspore.numpy as np
        >>> from mindspore import ops, Tensor
        >>> from mindspore.text.modules.attentions import LocationAwareAttention
        >>> hidden_dim = 20
        >>> standard_normal = ops.StandardNormal(seed=0)
        >>> query = standard_normal((batch_size, 1, hidden_dims))
        >>> value = standard_normal((batch_size, seq_len, hidden_dims))
        >>> last_attn = standard_normal((batch_size, seq_len))
        >>> net = LocationAwareAttention(
            hidden_dim=20,
            smoothing=False)
        >>> mask_shape = (batch_size, seq_len)
        >>> mask = Tensor(np.ones(mask_shape), mindspore.bool_)
        >>> net.set_mask(mask)
        >>> cont, attn = net(query, value, last_attn)
        >>> print(cont.shape, attn.shape)
        (2, 1, 20) (2, 40)
    """
    def __init__(self, hidden_dim, smoothing=False):
        r"""
        Initializes an instance of the LocationAwareAttention class.
        
        Args:
            self: The LocationAwareAttention object itself.
            hidden_dim (int): The dimensionality of the hidden state.
            smoothing (bool, optional): Flag indicating whether to apply smoothing. Defaults to False.
            
        Returns:
            None. This method does not return any value.
            
        Raises:
            None.
        
        This method initializes the LocationAwareAttention object with the specified hidden dimension and smoothing flag. It sets up the following components:
        - conv (nn.Conv1d): A 1D convolutional layer with an input channel of 1, output channel of hidden_dim, kernel size of 3, padding mode of 'pad', padding size of 1, and bias.
        - w_linear (nn.Linear): A fully connected layer with input and output dimensions of hidden_dim, used for attention weights computation.
        - v_linear (nn.Linear): Another fully connected layer with input and output dimensions of hidden_dim, also used for attention weights computation.
        - fc_linear (nn.Linear): A fully connected layer with input dimension of hidden_dim and output dimension of 1, used for final attention score calculation.
        - bias (nn.Parameter): A learnable parameter used as bias in the attention calculation.
        - tanh (nn.Tanh): A hyperbolic tangent activation function used in the attention calculation.
        - softmax (nn.Softmax): A softmax activation function used to normalize attention weights across the input sequence.
        - mask (None): A variable to store an optional mask.
        - sigmoid (nn.Sigmoid): A sigmoid activation function.
        
        This method is called when a new LocationAwareAttention object is created and sets up the necessary components and parameters for attention calculation.
        """
        super().__init__()
        self.hidden_dim = hidden_dim
        self.smoothing = smoothing
        self.conv = nn.Conv1d(
            in_channels=1, out_channels=hidden_dim, kernel_size=3, pad_mode="pad", padding=1, bias=True)
        self.w_linear = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.v_linear = nn.Linear(hidden_dim, hidden_dim, bias=False)
        self.fc_linear = nn.Linear(hidden_dim, 1, bias=True)
        # Set bias parameter
        uniformreal = ops.UniformReal(seed=0)
        bias_layer = uniformreal((hidden_dim,))
        self.bias = Parameter(bias_layer)
        self.tanh = nn.Tanh()
        self.softmax = nn.Softmax(axis=-1)
        self.mask = None
        self.sigmoid = nn.Sigmoid()

    def set_mask(self, mask):
        """
        Set the mask

        Args:
        mask mindspore.Tensor[bool]: The mask vector.
        """
        self.mask = mask

    def forward(self, query, value, last_attn=None):
        """Location aware attention network forwardion.

        Args:
            query (mindspore.Tensor): Decoder hidden states,
                Shape=(batch_size, 1, decoder_dim).
            value (mindspore.Tensor): Encoder outputs,
                Shape=(batch_size, seq_len, encoder_dim).
            last_attn (mindspore.Tensor): Attention weight of previous step,
                Shape=(batch_size, seq_len).
        Returns:
            - **context** (mindspore.Tensor) - The context vector, Shape=(batch_size, 1, decoder_dim).
            - **attn** (mindspore.Tensor) - Attention weight of this step, Shape=(batch_size, seq_len).
        """
        batch_size, seq_len = query.shape[0], value.shape[1]
        if last_attn is None:
            last_attn = ops.zeros(batch_size, seq_len)
        conv_attn = self.conv(ops.expand_dims(last_attn, 1)).swapaxes(1, 2)
        scores = self.fc_linear(
            self.tanh(
                self.w_linear(query) + self.v_linear(value) + conv_attn + self.bias
            )
        ).squeeze(-1)
        if self.mask is not None:
            scores = ops.masked_fill(scores, self.mask == 0, -1e9)
        if self.smoothing:
            scores = self.sigmoid(scores)
            attn = ops.div(scores, ops.expand_dims(scores.sum(axis=-1), -1))
        else:
            attn = self.softmax(scores)
        context = ops.matmul(ops.expand_dims(attn, 1), value)
        return context, attn

__all__ = [
    "ScaledDotAttention",
    "SelfAttention",
    "BinaryAttention",
    "AdditiveAttention",
    "CosineAttention",
    "LinearAttention"
]
