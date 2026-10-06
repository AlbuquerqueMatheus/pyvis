import gc


def pytest_collection_finish(session):
    # Como no worker (worker.ts): o que já existe depois de carregar tudo fica fora das coletas,
    # e a coleta inteira que o rastreador faz no fim de cada execução fica barata.
    gc.freeze()
