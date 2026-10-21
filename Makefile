# Pipeline Matopiba. Cada alvo chama o executor em Python (src/matopiba/tarefas.py), que também
# funciona sem make:  python -m matopiba.tarefas <alvo>
PY ?= python
# ambiente opcional do HonestDiD (numpy < 2.4)
PY_HD ?= $(PY)

.PHONY: all etapa0 etapa1 etapa2 etapa3 etapa4 etapa5 etapa6 etapa7 analise testes lista honestdid

all:
	$(PY) -m matopiba.tarefas all testes

etapa0 etapa1 etapa2 etapa3 etapa4 etapa5 etapa6 etapa7 analise testes lista:
	$(PY) -m matopiba.tarefas $@

honestdid:
	$(PY_HD) -m matopiba.tarefas honestdid
