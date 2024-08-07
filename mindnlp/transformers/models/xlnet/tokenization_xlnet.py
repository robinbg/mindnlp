# coding=utf-8
# Copyright 2018 Google AI, Google Brain and Carnegie Mellon University Authors and the HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Tokenization classes for XLNet model."""

import os
import unicodedata
from shutil import copyfile
from typing import Any, Dict, List, Optional, Tuple

import sentencepiece as spm

from mindnlp.transformers.tokenization_utils import AddedToken, PreTrainedTokenizer
from mindnlp.utils import logging

logger = logging.get_logger(__name__)

VOCAB_FILES_NAMES = {"vocab_file": "spiece.model"}

PRETRAINED_VOCAB_FILES_MAP = {
    "vocab_file": {
        "xlnet/xlnet-base-cased": "https://huggingface.co/xlnet/xlnet-base-cased/resolve/main/spiece.model",
        "xlnet/xlnet-large-cased": "https://huggingface.co/xlnet/xlnet-large-cased/resolve/main/spiece.model",
    }
}

PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES = {
    "xlnet/xlnet-base-cased": None,
    "xlnet/xlnet-large-cased": None,
}

# Segments (not really needed)
SEG_ID_A = 0
SEG_ID_B = 1
SEG_ID_CLS = 2
SEG_ID_SEP = 3
SEG_ID_PAD = 4

SPIECE_UNDERLINE = "▁"


class XLNetTokenizer(PreTrainedTokenizer):
    """
    Construct an XLNet tokenizer. Based on [SentencePiece](https://github.com/google/sentencepiece).

    This tokenizer inherits from [`PreTrainedTokenizer`] which contains most of the main methods. Users should refer to
    this superclass for more information regarding those methods.

    Args:
        vocab_file (`str`):
            [SentencePiece](https://github.com/google/sentencepiece) file (generally has a .spm extension) that
            contains the vocabulary necessary to instantiate a tokenizer.
        do_lower_case (`bool`, *optional*, defaults to `False`):
            Whether to lowercase the input when tokenizing.
        remove_space (`bool`, *optional*, defaults to `True`):
            Whether to strip the text when tokenizing (removing excess spaces before and after the string).
        keep_accents (`bool`, *optional*, defaults to `False`):
            Whether to keep accents when tokenizing.
        bos_token (`str`, *optional*, defaults to `"<s>"`):
            The beginning of sequence token that was used during pretraining. Can be used a sequence classifier token.

            <Tip>

            When building a sequence using special tokens, this is not the token that is used for the beginning of
            sequence. The token used is the `cls_token`.

            </Tip>

        eos_token (`str`, *optional*, defaults to `"</s>"`):
            The end of sequence token.

            <Tip>

            When building a sequence using special tokens, this is not the token that is used for the end of sequence.
            The token used is the `sep_token`.

            </Tip>

        unk_token (`str`, *optional*, defaults to `"<unk>"`):
            The unknown token. A token that is not in the vocabulary cannot be converted to an ID and is set to be this
            token instead.
        sep_token (`str`, *optional*, defaults to `"<sep>"`):
            The separator token, which is used when building a sequence from multiple sequences, e.g. two sequences for
            sequence classification or for a text and a question for question answering. It is also used as the last
            token of a sequence built with special tokens.
        pad_token (`str`, *optional*, defaults to `"<pad>"`):
            The token used for padding, for example when batching sequences of different lengths.
        cls_token (`str`, *optional*, defaults to `"<cls>"`):
            The classifier token which is used when doing sequence classification (classification of the whole sequence
            instead of per-token classification). It is the first token of the sequence when built with special tokens.
        mask_token (`str`, *optional*, defaults to `"<mask>"`):
            The token used for masking values. This is the token used when training this model with masked language
            modeling. This is the token which the model will try to predict.
        additional_special_tokens (`List[str]`, *optional*, defaults to `['<eop>', '<eod>']`):
            Additional special tokens used by the tokenizer.
        sp_model_kwargs (`dict`, *optional*):
            Will be passed to the `SentencePieceProcessor.__init__()` method. The [Python wrapper for
            SentencePiece](https://github.com/google/sentencepiece/tree/master/python) can be used, among other things,
            to set:

            - `enable_sampling`: Enable subword regularization.
            - `nbest_size`: Sampling parameters for unigram. Invalid for BPE-Dropout.

                - `nbest_size = {0,1}`: No sampling is performed.
                - `nbest_size > 1`: samples from the nbest_size results.
                - `nbest_size < 0`: assuming that nbest_size is infinite and samples from the all hypothesis (lattice)
                using forward-filtering-and-backward-sampling algorithm.

            - `alpha`: Smoothing parameter for unigram sampling, and dropout probability of merge operations for
            BPE-dropout.

    Attributes:
        sp_model (`SentencePieceProcessor`):
            The *SentencePiece* processor that is used for every conversion (string, tokens and IDs).
    """
    vocab_files_names = VOCAB_FILES_NAMES
    pretrained_vocab_files_map = PRETRAINED_VOCAB_FILES_MAP
    max_model_input_sizes = PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES
    padding_side = "left"

    def __init__(
            self,
            vocab_file,
            do_lower_case=False,
            remove_space=True,
            keep_accents=False,
            bos_token="<s>",
            eos_token="</s>",
            unk_token="<unk>",
            sep_token="<sep>",
            pad_token="<pad>",
            cls_token="<cls>",
            mask_token="<mask>",
            additional_special_tokens=["<eop>", "<eod>"],
            sp_model_kwargs: Optional[Dict[str, Any]] = None,
            **kwargs,
    ) -> None:
        """
        Initialize an XLNetTokenizer object.

        Args:
            vocab_file (str): Path to the vocabulary file.
            do_lower_case (bool, optional): Whether to lowercase the input tokens. Defaults to False.
            remove_space (bool, optional): Whether to remove spaces in the input tokens. Defaults to True.
            keep_accents (bool, optional): Whether to keep accents in the input tokens. Defaults to False.
            bos_token (str, optional): Beginning of sentence token. Defaults to '<s>'.
            eos_token (str, optional): End of sentence token. Defaults to '</s>'.
            unk_token (str, optional): Unknown token. Defaults to '<unk>'.
            sep_token (str, optional): Separator token. Defaults to '<sep>'.
            pad_token (str, optional): Padding token. Defaults to '<pad>'.
            cls_token (str, optional): Classification token. Defaults to '<cls>'.
            mask_token (str, optional): Mask token. Defaults to '<mask>'.
            additional_special_tokens (list, optional): Additional special tokens to include.
                Defaults to ['<eop>', '<eod>'].
            sp_model_kwargs (Dict[str, Any], optional): SentencePiece model keyword arguments. Defaults to None.
            **kwargs: Additional keyword arguments.

        Returns:
            None

        Raises:
            TypeError: If the mask_token is not a string.
        """
        # Mask token behave like a normal word, i.e. include the space before it
        mask_token = AddedToken(mask_token, lstrip=True, special=True) if isinstance(mask_token, str) else mask_token

        self.sp_model_kwargs = {} if sp_model_kwargs is None else sp_model_kwargs

        self.do_lower_case = do_lower_case
        self.remove_space = remove_space
        self.keep_accents = keep_accents
        self.vocab_file = vocab_file

        self.sp_model = spm.SentencePieceProcessor(**self.sp_model_kwargs)
        self.sp_model.Load(vocab_file)

        super().__init__(
            do_lower_case=do_lower_case,
            remove_space=remove_space,
            keep_accents=keep_accents,
            bos_token=bos_token,
            eos_token=eos_token,
            unk_token=unk_token,
            sep_token=sep_token,
            pad_token=pad_token,
            cls_token=cls_token,
            mask_token=mask_token,
            additional_special_tokens=additional_special_tokens,
            sp_model_kwargs=self.sp_model_kwargs,
            **kwargs,
        )

        self._pad_token_type_id = 3

    @property
    def vocab_size(self):
        """
        Returns the vocabulary size of the XLNetTokenizer.

        Args:
            self (XLNetTokenizer): An instance of the XLNetTokenizer class.

        Returns:
            int: The vocabulary size of the tokenizer.

        Raises:
            None

        This method calculates and returns the size of the vocabulary used by the XLNetTokenizer.
        The vocabulary size is determined by the number of unique tokens present in the tokenizer's sp_model.

        Note:
            The vocabulary size represents the number of distinct tokens that the tokenizer can recognize and encode.

        Example:
            ```python
            >>> tokenizer = XLNetTokenizer()
            >>> size = tokenizer.vocab_size()
            >>> print(size)
            32000
            ```
        """
        return len(self.sp_model)

    def get_vocab(self):
        """
        Returns the vocabulary of the XLNetTokenizer.

        Args:
            self: The instance of the XLNetTokenizer class.

        Returns:
            dict:
                A dictionary containing the vocabulary of the XLNetTokenizer.
                The keys of the dictionary are the tokens, and the values are their corresponding indices.

        Raises:
            None.

        Example:
            ```python
            >>> tokenizer = XLNetTokenizer()
            >>> tokenizer.get_vocab()
            {'<s>': 0, '<pad>': 1, '</s>': 2, '<unk>': 3, '<mask>': 4, 'hello': 5, 'world': 6}
            ```
        """
        vocab = {self.convert_ids_to_tokens(i): i for i in range(self.vocab_size)}
        vocab.update(self.added_tokens_encoder)
        return vocab

    def __getstate__(self):
        """
        Method '__getstate__' in the class 'XLNetTokenizer'.

        Args:
            self (XLNetTokenizer): The instance of the XLNetTokenizer class.
                Represents the current XLNetTokenizer object.

        Returns:
            dict: This method returns a dictionary representing the state of the XLNetTokenizer object.
                The 'sp_model' key in the dictionary is set to None before returning.

        Raises:
            None.
        """
        state = self.__dict__.copy()
        state["sp_model"] = None
        return state

    def __setstate__(self, d):
        """
        This method __setstate__ is defined in the class XLNetTokenizer and is used to set the internal state of the
        object based on the provided dictionary 'd'.

        Args:
            self (XLNetTokenizer): The instance of the XLNetTokenizer class.
            d (dict): A dictionary containing the state information to be set. The keys and values in the dictionary
                are used to update the internal state of the XLNetTokenizer object.

        Returns:
            None. This method does not return any value.

        Raises:
            None:
                However, potential exceptions that could be raised include:

                - AttributeError: If the 'sp_model_kwargs' attribute is not found within the XLNetTokenizer object.
                - TypeError: If the provided 'd' parameter is not a dictionary.
                - Other exceptions related to the SentencePieceProcessor object creation or loading process may be
                raised from the spm.SentencePieceProcessor forwardor or Load method.
        """
        self.__dict__ = d

        # for backward compatibility
        if not hasattr(self, "sp_model_kwargs"):
            self.sp_model_kwargs = {}

        self.sp_model = spm.SentencePieceProcessor(**self.sp_model_kwargs)
        self.sp_model.Load(self.vocab_file)

    def preprocess_text(self, inputs):
        """
        This method preprocesses the input text according to the specified configuration settings.

        Args:
            self (XLNetTokenizer): The instance of the XLNetTokenizer class.
            inputs (str): The input text to be preprocessed. It should be a string representation.

        Returns:
            str: The preprocessed text based on the applied configuration settings.

        Raises:
            None
        """
        if self.remove_space:
            outputs = " ".join(inputs.strip().split())
        else:
            outputs = inputs
        outputs = outputs.replace("``", '"').replace("''", '"')

        if not self.keep_accents:
            outputs = unicodedata.normalize("NFKD", outputs)
            outputs = "".join([c for c in outputs if not unicodedata.combining(c)])
        if self.do_lower_case:
            outputs = outputs.lower()

        return outputs

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize a string."""
        text = self.preprocess_text(text)
        pieces = self.sp_model.encode(text, out_type=str)
        new_pieces = []
        for piece in pieces:
            if len(piece) > 1 and piece[-1] == str(",") and piece[-2].isdigit():
                cur_pieces = self.sp_model.EncodeAsPieces(piece[:-1].replace(SPIECE_UNDERLINE, ""))
                if piece[0] != SPIECE_UNDERLINE and cur_pieces[0][0] == SPIECE_UNDERLINE:
                    if len(cur_pieces[0]) == 1:
                        cur_pieces = cur_pieces[1:]
                    else:
                        cur_pieces[0] = cur_pieces[0][1:]
                cur_pieces.append(piece[-1])
                new_pieces.extend(cur_pieces)
            else:
                new_pieces.append(piece)

        return new_pieces

    def _convert_token_to_id(self, token):
        """Converts a token (str) in an id using the vocab."""
        return self.sp_model.PieceToId(token)

    def _convert_id_to_token(self, index):
        """Converts an index (integer) in a token (str) using the vocab."""
        return self.sp_model.IdToPiece(index)

    def convert_tokens_to_string(self, tokens):
        """Converts a sequence of tokens (strings for sub-words) in a single string."""
        out_string = "".join(tokens).replace(SPIECE_UNDERLINE, " ").strip()
        return out_string

    def _decode(
            self,
            token_ids: List[int],
            skip_special_tokens: bool = False,
            clean_up_tokenization_spaces: bool = None,
            spaces_between_special_tokens: bool = True,
            **kwargs,
    ) -> str:
        """
        This method decodes a list of token IDs into a string representation.

        Args:
            self: The instance of the XLNetTokenizer class.
            token_ids (List[int]): A list of token IDs to be decoded into a string.
            skip_special_tokens (bool): A flag indicating whether to skip special tokens during decoding.
                Defaults to False.
            clean_up_tokenization_spaces (bool): A flag indicating whether to clean up tokenization spaces in the
                decoded text. If None, the value is determined by the clean_up_tokenization_spaces attribute of
                the XLNetTokenizer instance.
            spaces_between_special_tokens (bool): A flag indicating whether to include spaces between special tokens
                in the decoded text. Defaults to True.
            **kwargs: Additional keyword arguments. 'use_source_tokenizer' is a supported argument to control the
                use of the source tokenizer during decoding.

        Returns:
            str: The decoded string representation of the token IDs.

        Raises:
            None
        """
        self._decode_use_source_tokenizer = kwargs.pop("use_source_tokenizer", False)

        filtered_tokens = self.convert_ids_to_tokens(token_ids, skip_special_tokens=skip_special_tokens)

        # To avoid mixing byte-level and unicode for byte-level BPT
        # we need to build string separately for added tokens and byte-level tokens
        # cf. https://github.com/huggingface/transformers/issues/1133
        sub_texts = []
        current_sub_text = []
        for token in filtered_tokens:
            if skip_special_tokens and token in self.all_special_ids:
                continue
            if token in self.added_tokens_encoder:
                if current_sub_text:
                    sub_texts.append(self.convert_tokens_to_string(current_sub_text))
                    current_sub_text = []
                sub_texts.append(token)
            else:
                current_sub_text.append(token)
        if current_sub_text:
            sub_texts.append(self.convert_tokens_to_string(current_sub_text))

        # Mimic the behavior of the Rust tokenizer:
        # By default, there are no spaces between special tokens
        text = "".join(sub_texts)

        clean_up_tokenization_spaces = (
            clean_up_tokenization_spaces
            if clean_up_tokenization_spaces is not None
            else self.clean_up_tokenization_spaces
        )
        if clean_up_tokenization_spaces:
            clean_text = self.clean_up_tokenization(text)
            return clean_text
        else:
            return text

    def build_inputs_with_special_tokens(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. An XLNet sequence has the following format:

        - single sequence: `X <sep> <cls>`
        - pair of sequences: `A <sep> B <sep> <cls>`

        Args:
            token_ids_0 (`List[int]`):
                List of IDs to which the special tokens will be added.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of [input IDs](../glossary#input-ids) with the appropriate special tokens.
        """
        sep = [self.sep_token_id]
        cls = [self.cls_token_id]
        if token_ids_1 is None:
            return token_ids_0 + sep + cls
        return token_ids_0 + sep + token_ids_1 + sep + cls

    def get_special_tokens_mask(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None,
            already_has_special_tokens: bool = False
    ) -> List[int]:
        """
        Retrieve sequence ids from a token list that has no special tokens added. This method is called when adding
        special tokens using the tokenizer `prepare_for_model` method.

        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.
            already_has_special_tokens (`bool`, *optional*, defaults to `False`):
                Whether or not the token list is already formatted with special tokens for the model.

        Returns:
            `List[int]`: A list of integers in the range [0, 1]: 1 for a special token, 0 for a sequence token.
        """
        if already_has_special_tokens:
            return super().get_special_tokens_mask(
                token_ids_0=token_ids_0, token_ids_1=token_ids_1, already_has_special_tokens=True
            )

        if token_ids_1 is not None:
            return ([0] * len(token_ids_0)) + [1] + ([0] * len(token_ids_1)) + [1, 1]
        return ([0] * len(token_ids_0)) + [1, 1]

    def create_token_type_ids_from_sequences(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Create a mask from the two sequences passed to be used in a sequence-pair classification task. An XLNet
        sequence pair mask has the following format:
        ```
        0 0 0 0 0 0 0 0 0 0 0 1 1 1 1 1 1 1 1 1
        | first sequence    | second sequence |
        ```

        If `token_ids_1` is `None`, this method only returns the first portion of the mask (0s).

        Args:
            token_ids_0 (`List[int]`):
                List of IDs.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of [token type IDs](../glossary#token-type-ids) according to the given sequence(s).
        """
        sep = [self.sep_token_id]
        cls_segment_id = [2]

        if token_ids_1 is None:
            return len(token_ids_0 + sep) * [0] + cls_segment_id
        return len(token_ids_0 + sep) * [0] + len(token_ids_1 + sep) * [1] + cls_segment_id

    def save_vocabulary(self, save_directory: str, filename_prefix: Optional[str] = None) -> Tuple[str]:
        """
        Save the vocabulary of the XLNetTokenizer.

        Args:
            self (XLNetTokenizer): An instance of the XLNetTokenizer class.
            save_directory (str): The directory path where the vocabulary will be saved.
            filename_prefix (Optional[str]): An optional prefix for the filename of the saved vocabulary.
                Defaults to None.

        Returns:
            Tuple[str]: A tuple containing the path to the saved vocabulary file.

        Raises:
            FileNotFoundError: If the specified save_directory does not exist.
            PermissionError: If the specified save_directory is not accessible for writing.

        Note:
            - The saved vocabulary file will be named as per the following format:
            '<filename_prefix>-vocab.txt' if filename_prefix is provided, otherwise 'vocab.txt'.
            - If the provided save_directory is the same as the current vocabulary file's directory and
            the vocabulary file already exists, it will be copied to the save_directory.
            - If the current vocabulary file does not exist, a new vocabulary file will be created in the
            save_directory using the serialized model from the sp_model attribute of the tokenizer.

        Example:
            ```python
            >>> tokenizer = XLNetTokenizer()
            >>> save_dir = '/path/to/save'
            >>> prefix = 'english'
            >>> vocab_file = tokenizer.save_vocabulary(save_dir, prefix)
            >>> print(f"Vocabulary saved at: {vocab_file}")
            ```
        """
        if not os.path.isdir(save_directory):
            logger.error(f"Vocabulary path ({save_directory}) should be a directory")
            return
        out_vocab_file = os.path.join(
            save_directory, (filename_prefix + "-" if filename_prefix else "") + VOCAB_FILES_NAMES["vocab_file"]
        )

        if os.path.abspath(self.vocab_file) != os.path.abspath(out_vocab_file) and os.path.isfile(self.vocab_file):
            copyfile(self.vocab_file, out_vocab_file)
        elif not os.path.isfile(self.vocab_file):
            with open(out_vocab_file, "wb") as fi:
                content_spiece_model = self.sp_model.serialized_model_proto()
                fi.write(content_spiece_model)

        return (out_vocab_file,)

__all__ = ['XLNetTokenizer']
