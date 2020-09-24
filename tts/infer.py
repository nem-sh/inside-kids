# -*- coding: utf-8 -*-


import os
import sys
from pathlib import Path
from pprint import pprint

os.environ['CUDA_VISIBLE_DEVICES'] = '-1' # USE CPU

import yaml
import json
import numpy as np
import torch
import tensorflow as tf
from sklearn.preprocessing import StandardScaler

sys.path.append('./content/TensorflowTTS')
from tensorflow_tts.processor.ljspeech import LJSpeechProcessor
from tensorflow_tts.processor.ljspeech import symbols as tensorflowtts_symbols
from tensorflow_tts.processor.ljspeech import _symbol_to_id

from tensorflow_tts.configs import MultiBandMelGANGeneratorConfig
from tensorflow_tts.models import TFMelGANGenerator
from tensorflow_tts.models import TFPQMF
sys.path.remove('./content/TensorflowTTS')

sys.path.append('./content/glow-tts')
from utils import HParams, load_checkpoint
from text import symbols as glow_tts_symbols, text_to_sequence
from audio_processing import dynamic_range_decompression
from models import FlowGenerator
sys.path.remove('./content/glow-tts')

SAMPLING_RATE = 22050
processor = LJSpeechProcessor(None, "korean_cleaners")

def load_glow_tts(config_path, checkpoint_path):
    with open(config_path, "r") as f:
        data = f.read()
    config = json.loads(data)

    hparams = HParams(**config)
    model = FlowGenerator(
        len(glow_tts_symbols),
        out_channels=hparams.data.n_mel_channels,
        **hparams.model
    ).to("cpu")

    load_checkpoint(checkpoint_path, model)
    model.decoder.store_inverse() # do not calcuate jacobians for fast decoding
    _ = model.eval()

    return model

def inference_glow_tts(text, model, noise_scale=0.333, length_scale=0.9):
    sequence = np.array(text_to_sequence(text, ['korean_cleaners']))[None, :]
    x_tst = torch.autograd.Variable(torch.from_numpy(sequence)).cpu().long()
    x_tst_lengths = torch.tensor([x_tst.shape[1]]).cpu()
    with torch.no_grad():
        (y_gen_tst, *r), attn_gen, *_ = model(x_tst, x_tst_lengths, gen=True, noise_scale=noise_scale, length_scale=length_scale)
    return y_gen_tst

def convert_mel(mel):
    converted = mel.float().data.cpu().numpy()
    converted = np.expand_dims(np.transpose(converted[0]), axis=0)
    return converted

def normalize_mel(mel, mean, sigma):
    normalized = dynamic_range_decompression(mel)
    normalized = convert_mel(normalized)
    normalized = (np.log10(normalized) - mean) / sigma
    return normalized

def load_mb_melgan(config_path, model_path):
    with open(config_path) as f:
        raw_config = yaml.load(f, Loader=yaml.Loader)
        mb_melgan_config = MultiBandMelGANGeneratorConfig(**raw_config["generator_params"])
        mb_melgan = TFMelGANGenerator(config=mb_melgan_config, name='melgan_generator')
        mb_melgan._build()
        mb_melgan.load_weights(model_path)
        pqmf = TFPQMF(config=mb_melgan_config, name="pqmf")
    return (mb_melgan, pqmf)

def load_stats(stats_path):
    mean, scale = np.load(stats_path)
    sigma = np.sqrt(scale)
    return mean, sigma

def synthesis(mb_melgan, pqmf, mel):
    generated_subbands = mb_melgan(mel)
    generated_audios = pqmf.synthesis(generated_subbands)
    return generated_audios[0, :, 0]

def generate_audio_glow_tts(text, noise_scale=0.333, length_scale=0.9):
    mel_original = inference_glow_tts(text, glow_tts, noise_scale, length_scale)
    mel_nomalized = normalize_mel(mel_original, mb_mean, mb_sigma)
    audio = synthesis(mb_melgan, pqmf, mel_nomalized)
    return audio

def generate_audio_fastspeech2(text):
    mel = inference_fastspeech2(text, fastspeech2)
    audio = synthesis(mb_melgan, pqmf, mel)
    return audio

import sys
import re
from unicodedata import normalize

sys.path.append('./content/g2pK')
import g2pk
sys.path.remove('./content/g2pK')

all_symbols = set(tensorflowtts_symbols + glow_tts_symbols)

g2p = g2pk.G2p()

def normalize_text(text):
    text = simple_replace(text)
    text = g2p.idioms(text)
    text = g2pk.english.convert_eng(text, g2p.cmu)
    text = g2pk.utils.annotate(text, g2p.mecab)
    text = g2pk.numerals.convert_num(text)
    text = re.sub("/[PJEB]", "", text)
    text = eng_cap(text)

    text = normalize('NFD', text)
    for pos, char in enumerate(text):
        if char not in all_symbols:
            text = text[:pos] + ' ' + text[pos + 1:]
    text = normalize('NFC', text)
    return text

def split_text(text):
    texts = []
    pi = 0
    for ci in range(len(text)):
        if text[ci] in ',;:':
            # replace character to dot
            text = text[:ci] + '.' + text[ci + 1:]
            continue
        if text[ci] in '.!?\n':
            texts.append(text[pi:ci + 1])
            pi = ci + 1
    texts.append(text[pi:])
    return texts

def eng_cap(text):
    text = re.sub(r'(a|A)', "에이", text)
    text = re.sub(r'(b|B)', "비", text)
    text = re.sub(r'(c|C)', "씨", text)
    text = re.sub(r'(d|D)', "디", text)
    text = re.sub(r'(e|E)', "이", text)
    text = re.sub(r'(f|F)', "에프", text)
    text = re.sub(r'(g|G)', "쥐", text)
    text = re.sub(r'(h|H)', "에이치", text)
    text = re.sub(r'(i|I)', "아이", text)
    text = re.sub(r'(j|J)', "제이", text)
    text = re.sub(r'(k|K)', "케이", text)
    text = re.sub(r'(l|L)', "엘", text)
    text = re.sub(r'(m|M)', "엠", text)
    text = re.sub(r'(n|N)', "엔", text)
    text = re.sub(r'(o|O)', "오", text)
    text = re.sub(r'(p|P)', "피", text)
    text = re.sub(r'(q|Q)', "큐", text)
    text = re.sub(r'(r|R)', "알", text)
    text = re.sub(r'(s|S)', "에스", text)
    text = re.sub(r'(t|T)', "티", text)
    text = re.sub(r'(u|U)', "유", text)
    text = re.sub(r'(v|V)', "브이", text)
    text = re.sub(r'(w|W)', "더블유", text)
    text = re.sub(r'(x|X)', "엑스", text)
    text = re.sub(r'(y|Y)', "와이", text)
    text = re.sub(r'(z|Z)', "지", text)

    return text

def simple_replace(text):
    # 중복된 문장 부호는 마지막 문장부호로 변경
    text = re.sub(r'[.?!]+\?', "?", text)
    text = re.sub(r'[.?!]+!', "!", text)
    text = re.sub(r'[.?!]+\.', ".", text)

    # 기본 자모음
    text = re.sub(r'ㄱ', "기역", text)
    text = re.sub(r'ㄴ', "니은", text)
    text = re.sub(r'ㄷ', "디귿", text)
    text = re.sub(r'ㄹ', "리을", text)
    text = re.sub(r'ㅁ', "미음", text)
    text = re.sub(r'ㅂ', "비읍", text)
    text = re.sub(r'ㅅ', "시옷", text)
    text = re.sub(r'ㅇ', "이응", text)
    text = re.sub(r'ㅈ', "지읒", text)
    text = re.sub(r'ㅊ', "치읓", text)
    text = re.sub(r'ㅋ', "키읔", text)
    text = re.sub(r'ㅌ', "티읕", text)
    text = re.sub(r'ㅍ', "피읖", text)
    text = re.sub(r'ㅎ', "히읗", text)
    text = re.sub(r'ㄲ', "쌍기역", text)
    text = re.sub(r'ㄸ', "쌍디귿", text)
    text = re.sub(r'ㅃ', "쌍비읍", text)
    text = re.sub(r'ㅆ', "쌍시옷", text)
    text = re.sub(r'ㅉ', "쌍지읒", text)
    text = re.sub(r'ㄳ', "기역시옷", text)
    text = re.sub(r'ㄵ', "니은지읒", text)
    text = re.sub(r'ㄶ', "니은히읗", text)
    text = re.sub(r'ㄺ', "리을기역", text)
    text = re.sub(r'ㄻ', "리을미음", text)
    text = re.sub(r'ㄼ', "리을비읍", text)
    text = re.sub(r'ㄽ', "리을시옷", text)
    text = re.sub(r'ㄾ', "리을티읕", text)
    text = re.sub(r'ㄿ', "리을피읍", text)
    text = re.sub(r'ㅀ', "리을히읗", text)
    text = re.sub(r'ㅄ', "비읍시옷", text)
    text = re.sub(r'ㅏ', "아", text)
    text = re.sub(r'ㅑ', "야", text)
    text = re.sub(r'ㅓ', "어", text)
    text = re.sub(r'ㅕ', "여", text)
    text = re.sub(r'ㅗ', "오", text)
    text = re.sub(r'ㅛ', "요", text)
    text = re.sub(r'ㅜ', "우", text)
    text = re.sub(r'ㅠ', "유", text)
    text = re.sub(r'ㅡ', "으", text)
    text = re.sub(r'ㅣ', "이", text)
    text = re.sub(r'ㅐ', "애", text)
    text = re.sub(r'ㅒ', "얘", text)
    text = re.sub(r'ㅔ', "에", text)
    text = re.sub(r'ㅖ', "예", text)
    text = re.sub(r'ㅘ', "와", text)
    text = re.sub(r'ㅙ', "왜", text)
    text = re.sub(r'ㅚ', "외", text)
    text = re.sub(r'ㅝ', "워", text)
    text = re.sub(r'ㅞ', "웨", text)
    text = re.sub(r'ㅟ', "위", text)
    text = re.sub(r'ㅢ', "의", text)

    return text

def process_text(text):
    texts = split_text(text)
    results = []
    for text in texts:
        text = normalize_text(text)
        if text:
            results.append(text)
    return results

"""## 3. 학습한 모델 불러오기

학습한 Glow-TTS와 Multi-band MelGAN 모델을 불러옵니다.

만약 다른 체크포인트에서 불러오시려면 아래 코드에서 경로를 적절하게 수정합니다.
"""

glow_tts = load_glow_tts(
    config_path='/home/ubuntu/tts-test/tts/content/data/glow-tts/config.json',
    checkpoint_path='/home/ubuntu/tts-test/tts/content/data/glow-tts/G_3555.pth'
)

mb_mean, mb_sigma = load_stats(
    stats_path='/home/ubuntu/tts-test/tts/content/data/mb-melgan/stats.npy'
)

mb_melgan, pqmf = load_mb_melgan(
    config_path='/home/ubuntu/tts-test/tts/content/data/mb-melgan/config.yml',
    model_path='/home/ubuntu/tts-test/tts/content/data/mb-melgan/generator-675257.h5'
)

"""## 4. 음성 합성

실제 음성 합성을 수행합니다.

`long_text`의 값을 변경하여 다른 문장의 합성도 시도해보실 수 있습니다.
"""

long_text = """
아래 문장들은 모델 학습을 위해 사용하지 않은 문장들입니다.

서울특별시 특허허가과 허가과장 허과장.
경찰청 철창살은 외철창살이고 검찰청 철창살은 쌍철창살이다.
지향을 지양으로 오기하는 일을 지양하는 언어 습관을 지향해야 한다.
그러니까 외계인이 우리 생각을 읽고 우리 생각을 우리가 다시 생각토록 해서 그 생각이 마치 우리가 생각한 것인 것처럼 속였다는 거냐?

안 촉촉한 초코칩 나라에 살던 안 촉촉한 초코칩이 촉촉한 초코칩 나라의 촉촉한 초코칩을 보고 촉촉한 초코칩이 되고 싶어서 촉촉한 초코칩 나라에 갔는데 촉촉한 초코칩 나라의 촉촉한 문지기가 넌 촉촉한 초코칩이 아니고 안 촉촉한 초코칩이니까 안 촉촉한 초코칩 나라에서 살라고 해서 안 촉촉한 초코칩은 촉촉한 초코칩이 되는 것을 포기하고 안 촉촉한 눈물을 흘리며 안 촉촉한 초코칩 나라로 돌아갔다.
"""

import IPython.display as ipd
# from scipy.io.wavfile import write
import librosa
for text in process_text(long_text):
    text = text.strip()
    if text:
        print(text)
        audio = generate_audio_glow_tts(text, noise_scale=0.333, length_scale=0.9)
        type(audio)
        print(audio.numpy)
        # print(audiofile.data)
        librosa.output.write_wav(text+'.wav', audio.numpy(), 22050)
        # ipd.display(ipd.Audio(audio, rate=SAMPLING_RATE))