import io
import random
import re
import sys
import tokenize
import warnings
from pathlib import Path

import pytest

from pyvis_motor.privacidade import TEXTO, _por_leitura_propria, _por_tokenize, forma_canonica, higienizar
from test_estrutura import EXEMPLOS

CORPUS = sorted((Path(__file__).resolve().parent / "corpus").glob("*.py"))
NOMES = [e["titulo"] for e in EXEMPLOS] + [arquivo.name for arquivo in CORPUS]
PROGRAMAS = [e["codigo"] for e in EXEMPLOS] + [arquivo.read_text(encoding="utf-8") for arquivo in CORPUS]


def test_nome_em_print_vira_texto():
    assert higienizar('print("Oi, Maria")\n') == "print(<texto>)"
    assert higienizar("nome = 'Bia'\nprint('Olá', nome)\n") == "nome = <texto>\nprint(<texto>, nome)"


def test_comentarios_somem_e_a_linha_fica():
    codigo = "# Feito pela Maria da Silva\nx = 1  # a Bia ajudou\n\n# fim\ny = 2\n"
    assert higienizar(codigo) == "\nx = 1\n\n\ny = 2"


def test_comentario_com_aspas_e_texto_com_cerquilha():
    assert higienizar("x = 1  # it's Maria's\n") == "x = 1"
    assert higienizar('print("#1 é a Ana", \'#2\')\n') == "print(<texto>, <texto>)"


@pytest.mark.parametrize(
    "codigo",
    [
        'print(f"Olá {nome}, sou a Maria")\n',
        "print(F'Maria tem {idade} anos')\n",
        'print(f"{nome!r:>{largura}} e {{Maria}}")\n',
        'print(rf"Maria\\{x}")\n',
        "print(f'{\"Maria\"}')\n",
    ],
)
def test_f_string_inteira_vira_texto(codigo):
    assert higienizar(codigo) == "print(<texto>)"


@pytest.mark.parametrize(
    "codigo",
    ['print(f"{"Maria"}")\n', 'print(f"{dados["Maria"]} e {f\'{outro["Maria"]}\'}")\n'],
)
def test_f_string_com_aspas_iguais_dentro(codigo):
    # Python válido só a partir do 3.12. No 3.11 o tokenize lê pela metade, e a
    # leitura própria apaga a linha toda; nos dois casos, nada vaza.
    esperado = "print(<texto>)" if sys.version_info >= (3, 12) else "<texto>"
    assert higienizar(codigo) == esperado


def test_f_string_de_varias_linhas():
    codigo = 'msg = f"""Olá {nome},\nassinado: Maria\n{data}"""\nprint(msg)\n'
    assert higienizar(codigo) == "msg = <texto>\nprint(msg)"


def test_aspas_triplas_com_nomes():
    codigo = '"""Programa da Maria.\n\nTelefone da Bia: ninguém sabe.\n"""\nx = \'\'\'Ana\nJoão\'\'\'\nprint(x)\n'
    assert higienizar(codigo) == "<texto>\nx = <texto>\nprint(x)"


@pytest.mark.parametrize("prefixo", ["r", "R", "b", "B", "rb", "Rb", "bR", "u", "U", "fr", "Rf"])
def test_prefixos(prefixo):
    assert higienizar(f'x = {prefixo}"Maria"\n') == "x = <texto>"


def test_t_string_vira_texto_em_toda_versao():
    # No 3.14 é TSTRING; antes dele, o nome t seguido de um texto.
    assert higienizar('x = t"Olá {nome}, Maria"\n') == "x = <texto>"


def test_textos_colados():
    assert higienizar('x = "Ma" "ria"\ny = "a""b"\n') == "x = <texto> <texto>\ny = <texto><texto>"


def test_nomes_de_variaveis_e_acentos_ficam():
    codigo = 'ação = input("Seu nome? ")\nprint("Oi", ação)\nfor número in range(3):\n    print(número)\n'
    assert higienizar(codigo) == (
        "ação = input(<texto>)\nprint(<texto>, ação)\nfor número in range(3):\n    print(número)"
    )


def test_numero_longo_vira_numero():
    codigo = "tel = 11987654321\ncpf = 123_456_789_00\nx = 1234567\npi = 3.14159265\nh = 0x12345678\n"
    assert higienizar(codigo) == "tel = <numero>\ncpf = <numero>\nx = 1234567\npi = 3.14159265\nh = 0x12345678"


def test_quebras_de_linha_do_windows_e_do_mac_antigo():
    assert higienizar('x = "Ana"\r\ny = 2  # Bia\r\n') == "x = <texto>\ny = 2"
    assert higienizar('x = "Ana"\ry = 2\r') == "x = <texto>\ny = 2"


def test_codigo_vazio_e_so_comentario():
    assert higienizar("") == ""
    assert higienizar("# Maria\n") == ""


# --- Código com erro: a higiene não pode falhar nem vazar ----------------------


@pytest.mark.parametrize(
    "codigo, esperado",
    [
        # Texto sem fechar: a linha toda vira <texto>, o resto do programa fica.
        ('print("Olá Maria)\nx = 1\n', "<texto>\nx = 1"),
        ('if x:\n    print("Olá Maria)\nx = 1\n', "if x:\n    <texto>\nx = 1"),
        # Sem a primeira aspa, Maria pareceria código. No código quebrado, toda
        # linha com texto vira <texto>.
        ('print(Olá Maria")\nprint("tchau")\n', "<texto>\n<texto>"),
        ('print("Oi", Maria")\n', "<texto>"),
        ("dados = {Maria': 1, 'y': 'a\\'Bia'}\n", "<texto>"),
        # Aspas triplas sem fechar apagam tudo.
        ('x = 1\ndoc = """Maria\nBia\n', "<texto>"),
        ('doc = ""Maria\nBia\n"""\n', "<texto>"),
        # Erros que não envolvem textos: as linhas sem texto ficam.
        ('x = [1, 2\nprint("Maria")  # Bia\n', "x = [1, 2\n<texto>"),
        ('if x:\n        y = "Ana"\n    z = "Maria"\n    w = 2\n', "if x:\n        <texto>\n    <texto>\n    w = 2"),
        ('x = "Ana"\0  # Bia\n', "<texto>"),
    ],
)
def test_codigo_com_erro(codigo, esperado):
    assert higienizar(codigo) == esperado


def test_caractere_estranho():
    # No 3.11, $ é ERRORTOKEN (leitura própria); no 3.12+, o tokenize aceita.
    assert higienizar("x = $ 'Maria' ? 2  # Bia\n") in ("<texto>", "x = $ <texto> ? 2")


SEGREDO = "Zuleica"
PROGRAMA_COM_SEGREDO = (
    "# Programa da Zuleica\n"
    'nome = "Zuleica"\n'
    "apelido = 'Zuleica Silva'\n"
    'print(f"Olá {nome}, eu sou a Zuleica!", "x")\n'
    'doc = """Feito por\n'
    "Zuleica\n"
    '"""\n'
    "print(nome)  # Zuleica de novo\n"
    "dados = {'Zuleica': 1, \"y\": 'a\\'Zuleica'}\n"
    "tel = 11987654321\n"
)
PEDACOS = [SEGREDO[i : i + 4] for i in range(len(SEGREDO) - 3)]
# Posições dentro de comentários (depois do #): uma quebra de linha ali faz o
# resto do comentário virar código de verdade, como apagar o #.
DENTRO_DE_COMENTARIO = {
    posicao
    for inicio in [i for i, c in enumerate(PROGRAMA_COM_SEGREDO) if c == "#"]
    for posicao in range(inicio + 1, PROGRAMA_COM_SEGREDO.index("\n", inicio) + 1)
}


def _vazou(codigo):
    saida = higienizar(codigo)
    return [pedaco for pedaco in PEDACOS if pedaco in saida]


def test_programa_com_segredo_nao_vaza():
    assert not _vazou(PROGRAMA_COM_SEGREDO)
    assert "98765" not in higienizar(PROGRAMA_COM_SEGREDO)
    assert "nome" in higienizar(PROGRAMA_COM_SEGREDO)


def test_cortado_em_qualquer_ponto_nao_vaza():
    for fim in range(len(PROGRAMA_COM_SEGREDO) + 1):
        assert not _vazou(PROGRAMA_COM_SEGREDO[:fim]), fim


def test_sem_um_caractere_qualquer_nao_vaza():
    # Tirar o # transforma o comentário em código de verdade: esse caso fica de fora.
    for i, c in enumerate(PROGRAMA_COM_SEGREDO):
        if c == "#":
            continue
        assert not _vazou(PROGRAMA_COM_SEGREDO[:i] + PROGRAMA_COM_SEGREDO[i + 1 :]), i


@pytest.mark.parametrize("extra", ['"', "'", "\n", "\\", "{", "}"])
def test_com_um_caractere_a_mais_nao_vaza(extra):
    for i in range(len(PROGRAMA_COM_SEGREDO) + 1):
        if extra == "\n" and i in DENTRO_DE_COMENTARIO:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # o tokenize avisa de escapes inválidos como \{
            assert not _vazou(PROGRAMA_COM_SEGREDO[:i] + extra + PROGRAMA_COM_SEGREDO[i:]), i


def test_lixo_qualquer_nao_quebra_nem_deixa_aspa_ou_comentario():
    pedacos = list("abcfrtFRB019_ ()[]{}:=+-*/.,\\#'\"\n\t\r\0çã€$?")
    pedacos += ['"""', "'''", 'f"', "rb'", "{{", "\\\n", "if x:\n"]
    sorteio = random.Random(2026)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # o tokenize avisa de escapes inválidos
        for _ in range(2000):
            codigo = "".join(sorteio.choice(pedacos) for _ in range(sorteio.randint(0, 40)))
            limpo = higienizar(codigo)
            assert not set("'\"#") & set(limpo + forma_canonica(codigo)), codigo
            assert higienizar(limpo) == limpo, codigo


# --- Os dois caminhos concordam nos programas de verdade -----------------------


def _tokens(codigo):
    return list(tokenize.generate_tokens(io.StringIO(codigo).readline))


def test_programas_foram_lidos():
    assert len(PROGRAMAS) >= 50


@pytest.mark.parametrize("codigo", PROGRAMAS, ids=NOMES)
def test_leitura_propria_acha_os_mesmos_textos_que_o_tokenize(codigo):
    # Em código válido, a leitura própria só difere por apagar a linha inteira
    # onde há texto: as linhas, os comentários e os textos achados são os mesmos.
    texto = codigo.replace("\r\n", "\n")
    lido = _por_tokenize(texto)
    assert lido is not None
    esperado = [
        re.match(r"[ \t]*", linha).group() + TEXTO if TEXTO in linha else linha for linha in lido[0].split("\n")
    ]
    assert _por_leitura_propria(texto).split("\n") == esperado


@pytest.mark.parametrize("codigo", PROGRAMAS, ids=NOMES)
def test_saida_nao_tem_texto_nem_comentario_e_guarda_os_nomes(codigo):
    limpo = higienizar(codigo)
    assert not [t for t in _tokens(limpo) if tokenize.tok_name[t.type] in ("STRING", "COMMENT", "FSTRING_START")]
    # Os nomes de dentro das f-strings somem junto com elas; os outros ficam, na mesma ordem.
    assert _nomes_fora_de_texto(limpo.replace(TEXTO, "0")) == _nomes_fora_de_texto(codigo)


def _nomes_fora_de_texto(codigo):
    nomes, dentro = [], 0
    for token in _tokens(codigo):
        tipo = tokenize.tok_name[token.type]
        if tipo == "FSTRING_START":
            dentro += 1
        elif tipo == "FSTRING_END":
            dentro -= 1
        elif tipo == "NAME" and not dentro:
            nomes.append(token.string)
    return nomes


@pytest.mark.parametrize(
    "codigo", PROGRAMAS + [PROGRAMA_COM_SEGREDO, 'print("Oi Maria)\n'], ids=NOMES + ["segredo", "quebrado"]
)
def test_higienizar_duas_vezes_da_o_mesmo(codigo):
    assert higienizar(higienizar(codigo)) == higienizar(codigo)


# --- Forma canônica (base do code_hash) -----------------------------------------


def test_forma_canonica_ignora_espacos_comentarios_e_conteudo_de_texto():
    a = 'nota = 7\nif nota>=6:\n  print("Passou, Ana")\n'
    b = '# da Bia\nnota = 7\n\nif nota >= 6 :   # confere\n        print( "Tente, Maria" )\n'
    assert forma_canonica(a) == forma_canonica(b) == "nota = 7\nif nota >= 6 :\n    print ( <texto> )"


def test_forma_canonica_muda_quando_o_programa_muda():
    base = forma_canonica("for i in range(3):\n    print(i)\n")
    assert forma_canonica("for i in range(4):\n    print(i)\n") != base
    assert forma_canonica("for i in range(3):\n    pass\nprint(i)\n") != base
    assert forma_canonica("for i in range(3):\nprint(i)\n") != base  # o recuo conta


def test_forma_canonica_junta_comando_de_varias_linhas():
    assert forma_canonica("x = [1,\n     2,\n     3]\n") == "x = [ 1 , 2 , 3 ]"


def test_forma_canonica_de_codigo_com_erro_tambem_e_higienizada():
    forma = forma_canonica('print("Olá Maria)\nx  =  1\n')
    assert forma == "<texto>\nx = 1"
    assert "Maria" not in forma_canonica('doc = """Maria\n')


@pytest.mark.parametrize("codigo", PROGRAMAS, ids=NOMES)
def test_forma_canonica_nao_tem_texto(codigo):
    forma = forma_canonica(codigo)
    assert "#" not in forma
    assert '"' not in forma and "'" not in forma


@pytest.mark.skipif(sys.version_info < (3, 12), reason="f-string com aspas iguais dentro só existe no 3.12+")
def test_f_string_com_aspas_iguais_usa_o_tokenize_no_312():
    assert _por_tokenize('x = f"{d["Maria"]}"\n') is not None
    assert higienizar('x = f"{d["Maria"]}"\n') == "x = <texto>"
