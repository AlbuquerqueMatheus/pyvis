import itertools

import pytest

from pyvis_motor import apelido
from pyvis_motor.apelido import ANIMAIS, CORES, NUMEROS, gerar, sugestoes, validar


def test_exemplo_do_roteiro_e_valido():
    assert validar("Tucano Azul 7")


def test_gerar_e_deterministico_e_igual_em_toda_versao():
    # O valor fixo confere que o sorteio (sha256) é o mesmo no 3.11, no 3.14 e no Pyodide.
    assert gerar(7) == "Jabuti Anil 8"
    assert gerar(7) == gerar("7")
    assert gerar("sala-8A") == gerar("sala-8A")


def test_sem_semente_sai_um_apelido_valido_e_variado():
    sorteados = {gerar() for _ in range(8)}
    assert all(validar(a) for a in sorteados)
    assert len(sorteados) > 1


def test_todo_apelido_que_gerar_produz_e_aceito():
    assert all(validar(gerar(semente)) for semente in range(2000))


def test_toda_combinacao_das_listas_e_aceita_com_a_cor_no_genero_certo():
    total = 0
    for (animal, genero), (masculino, feminino), numero in itertools.product(ANIMAIS, CORES, NUMEROS):
        cor = masculino if genero == "m" else feminino
        assert validar(f"{animal} {cor} {numero}")
        total += 1
    assert total == len(ANIMAIS) * len(CORES) * len(NUMEROS) > 50_000


def test_cor_concorda_com_o_bicho():
    assert validar("Coruja Amarela 7")
    assert validar("Lobo Amarelo 7")
    assert not validar("Coruja Amarelo 7")
    assert not validar("Lobo Amarela 7")


@pytest.mark.parametrize(
    "texto",
    [
        "Maria Silva 7",
        "Tucano Azul",
        "Tucano Azul 7 ",
        " Tucano Azul 7",
        "Tucano  Azul 7",
        "tucano azul 7",
        "TUCANO AZUL 7",
        "Tucano Azul 07",
        "Tucano Azul 0",
        "Tucano Azul 100",
        "Tucano Azul -7",
        "Tucano Azul 24",
        "Tucano Azul 69",
        "Tucano Azul sete",
        "Tucano Azul 7 Maria",
        "Macaco Azul 7",
        "Veado Azul 7",
        "Tucano Preto 7",
        "Tucano\tAzul 7",
        "Tucano Azul ７",
        "",
    ],
)
def test_validar_recusa_o_que_nao_saiu_das_listas(texto):
    assert not validar(texto)


@pytest.mark.parametrize("valor", [None, 7, ["Tucano", "Azul", "7"], b"Tucano Azul 7"])
def test_validar_recusa_o_que_nao_e_texto(valor):
    assert not validar(valor)


# Bichos que viram xingamento, ofensa racista, piada com o corpo ou duplo sentido,
# bichos que são nome de gente e cores de pele.
PROIBIDAS = {
    "macaco", "mico", "gorila", "urubu", "veado", "burro", "jumento", "mula", "anta", "porco",
    "vaca", "galinha", "piranha", "cobra", "rato", "barata", "lesma", "toupeira", "hiena",
    "baleia", "elefante", "hipopótamo", "girafa", "foca", "gata", "cachorra", "perua", "pato",
    "peru", "pinto", "rola", "perereca", "periquita", "bicha", "gavião", "boto", "sapo",
    "ema", "joaninha", "joão-de-barro",
    "preto", "preta", "branco", "branca", "marrom", "pardo", "parda", "moreno", "morena",
    "rosa", "violeta", "celeste", "jade", "esmeralda", "vinho",
}


def test_listas_nao_tem_palavra_proibida():
    palavras = {animal.lower() for animal, _ in ANIMAIS} | {cor.lower() for par in CORES for cor in par}
    assert not palavras & PROIBIDAS
    assert not any("apost" in palavra for palavra in palavras)


def test_numeros_com_sentido_ruim_ficam_fora():
    assert {13, 14, 17, 18, 22, 24, 51, 69, 88}.isdisjoint(NUMEROS)
    assert 0 not in NUMEROS and 100 not in NUMEROS
    assert 7 in NUMEROS


def test_listas_sem_repeticao():
    assert len({animal for animal, _ in ANIMAIS}) == len(ANIMAIS)
    assert len(set(CORES)) == len(CORES)
    assert all(genero in ("m", "f") for _, genero in ANIMAIS)
    # Uma palavra por parte: validar() separa por espaço.
    assert all(" " not in animal for animal, _ in ANIMAIS)
    assert all(" " not in cor for par in CORES for cor in par)


def test_sugestoes_sao_diferentes_e_comecam_pelo_gerado():
    opcoes = sugestoes(42)
    assert len(opcoes) == 4
    assert opcoes[0] == gerar(42)
    assert len(set(opcoes)) == 4
    assert all(validar(a) for a in opcoes)
    assert sugestoes(42) == opcoes
    assert sugestoes(43) != opcoes
    assert len(sugestoes(42, 10)) == 10


@pytest.mark.parametrize("quantidade", [0, 21])
def test_sugestoes_com_quantidade_fora_do_limite(quantidade):
    with pytest.raises(ValueError):
        sugestoes(1, quantidade)


def test_apelidos_sao_curtos():
    for semente in range(500):
        texto = gerar(semente)
        assert len(texto.split(" ")) == 3
        assert len(texto) <= 24


def test_modulo_nao_usa_o_random_do_aluno():
    # O aluno pode chamar random.seed(): o apelido não pode depender disso.
    import random

    random.seed(1)
    primeiro = gerar(5)
    random.seed(2)
    assert gerar(5) == primeiro
    assert apelido.gerar(5) == primeiro
