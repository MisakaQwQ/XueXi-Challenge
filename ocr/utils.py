# coding: utf-8
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import os
import platform
import numpy as np


def data_dir_default():
    """

    :return: default data directory depending on the platform and environment variables
    """
    system = platform.system()
    if system == 'Windows':
        return os.path.join(os.environ.get('APPDATA'), 'cnocr')
    else:
        return os.path.join(os.path.expanduser("~"), '.cnocr')


def data_dir():
    """

    :return: data directory in the filesystem for storage, for example when downloading models
    """
    return os.getenv('CNOCR_HOME', data_dir_default())


def read_charset(charset_fp):
    alphabet = [None]
    # 第0个元素是预留id，在CTC中用来分割字符。它不对应有意义的字符
    with open(charset_fp, encoding='utf-8') as fp:
        for line in fp:
            alphabet.append(line.rstrip('\n'))
    # print('Alphabet size: %d' % len(alphabet))
    inv_alph_dict = {_char: idx for idx, _char in enumerate(alphabet)}
    # inv_alph_dict[' '] = inv_alph_dict['<space>']  # 对应空格
    return alphabet, inv_alph_dict


def normalize_img_array(img):
    """ rescale to [-1.0, 1.0] """
    # return (img / 255.0 - 0.5) * 2
    return (img - np.mean(img)) / (np.std(img) + 1e-6)
