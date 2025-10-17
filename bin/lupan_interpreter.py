# lupan_interpreter.py
# Interpretador Lupan (tradução por token + env com aliases/constantes)
import io
import sys
import tokenize
import unicodedata
import contextlib
import traceback
import importlib
import math
import codeop
import builtins

# ----------------------------
# Mapeamentos principais
# ----------------------------
# keywords: apenas palavras-chave que devem virar Python keywords
_KEYWORDS_RAW = {
    'se': 'if', 'senao': 'else', 'senão': 'else',
    'senaose': 'elif', 'senãose': 'elif',
    'enquanto': 'while', 'para': 'for', 'em': 'in',
    'funcao': 'def', 'função': 'def', 'classe': 'class',
    'retorne': 'return', 'construtor': '__init__', 'isto': 'self',
    'pare': 'break', 'continue': 'continue', 'passe': 'pass',
    'com': 'with', 'como': 'as',
    'importe': 'import', 'importa': 'import', 'de': 'from',
    'tente': 'try', 'exceto': 'except', 'finalmente': 'finally',
    'lance': 'raise', 'afirme': 'assert',
    'global': 'global', 'nao_local': 'nonlocal',
    'verdadeiro': 'True', 'falso': 'False', 'nulo': 'None',
    'e': 'and', 'ou': 'or', 'nao': 'not', 'não': 'not',
    'lambda': 'lambda', 'rendim': 'yield'
}

# Para comparação estável (sem acento)
def _norm(name: str) -> str:
    nf = unicodedata.normalize('NFD', name)
    no_accent = ''.join(ch for ch in nf if unicodedata.category(ch) != 'Mn')
    return no_accent.lower()

# Criar dicionário com chaves normalizadas
_KEYWORDS = { _norm(k): v for k, v in _KEYWORDS_RAW.items() }

# builtins aliases (colocados no env, apontando para objetos Python)
_BUILTIN_ALIASES = {
    'mostre': print, 'escreva': print, 'exiba': print,
    'pergunte': input, 'entrada': input, 'leia': input,
    'tamanho': len, 'len': len,
    'intervalo': range, 'range': range,
    'lista': list, 'dicionario': dict, 'conjunto': set, 'tupla': tuple,
    'ordem': sorted, 'soma': sum, 'minimo': min, 'maximo': max,
    'absoluto': abs, 'tipo': type, 'ajuda': help, 'abra': open
}

# constantes práticas
_CONSTANTES = {
    'infinito': math.inf,
    'menos_infinito': -math.inf,
    'nan': math.nan,
    'pi': math.pi,
    'euler': math.e
}

# ----------------------------
# Função de tradução (token-based)
# substitui apenas tokens do tipo NAME (preserva strings)
# ----------------------------
def traduzir(source: str) -> str:
    src_io = io.StringIO(source)
    try:
        tokens = list(tokenize.generate_tokens(src_io.readline))
    except Exception:
        # fallback simples
        return source

    out_tokens = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        ttype, tstring, start, end, line = tok

        if ttype == tokenize.NAME:
            normalized = _norm(tstring)
            # Lookahead: tratar "senao se" -> "elif"
            if normalized in ('senao', 'senão'):
                # procurar próximo token não vazio
                j = i + 1
                if j < len(tokens) and tokens[j].type == tokenize.NAME:
                    nxt = _norm(tokens[j].string)
                    if nxt == 'se':
                        # inserir 'elif' e pular o próximo token
                        newtok = tok._replace(string='elif')
                        out_tokens.append(newtok)
                        i += 2
                        continue

            if normalized in _KEYWORDS:
                new_name = _KEYWORDS[normalized]
                newtok = tok._replace(string=new_name)
                out_tokens.append(newtok)
            else:
                out_tokens.append(tok)
        else:
            out_tokens.append(tok)
        i += 1

    pycode = tokenize.untokenize(out_tokens)
    return pycode

# ----------------------------
# Interpreter com ambiente persistente
# ----------------------------
class LupanInterpreter:
    def __init__(self):
        # ambiente de execução persistente
        self.env = {'__name__': '__main__'}
        # popular aliases e constantes
        for name, obj in _BUILTIN_ALIASES.items():
            self.env[name] = obj
        for name, val in _CONSTANTES.items():
            self.env[name] = val
        # expor math e lupan_gfx (se disponível)
        self.env['math'] = math
        try:
            self.env['lupan_gfx'] = importlib.import_module('lupan_gfx')
        except Exception:
            pass

    def executar(self, source: str, filename: str = '<string>'):
        """Executa código Lupan (string), retorna (stdout, stderr, exception_info_or_None)."""
        py = traduzir(source)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout_buf):
                with contextlib.redirect_stderr(stderr_buf):
                    compiled = compile(py, filename, 'exec')
                    exec(compiled, self.env, self.env)
            return stdout_buf.getvalue(), stderr_buf.getvalue(), None
        except Exception:
            tb = traceback.format_exc()
            stderr_buf.write(tb)
            return stdout_buf.getvalue(), stderr_buf.getvalue(), sys.exc_info()

    def executar_arquivo(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        return self.executar(src, filename=path)

    # REPL (linha por linha, suporta blocos multiline via codeop.compile_command)
    def repl(self, banner: str = None):
        if banner is None:
            banner = "Lupan 1.0.0 (inspirado em Python)\nDigite 'sair()' para sair."
        print(banner)
        buffer_lines = []
        compile_cmd = codeop.compile_command
        prompt_primary = '>>> '
        prompt_cont = '... '
        while True:
            try:
                prompt = prompt_primary if not buffer_lines else prompt_cont
                line = input(prompt)
            except EOFError:
                print()
                break
            if line.strip() in ('sair()', 'exit()', 'quit()'):
                break
            buffer_lines.append(line)
            source = '\n'.join(buffer_lines) + '\n'
            # traduzir *o código acumulado* para Python antes de compilar
            py_source = traduzir(source)
            try:
                code_obj = compile_cmd(py_source, '<input>', 'single')
            except (SyntaxError, OverflowError) as e:
                print("Erro de sintaxe:", e)
                buffer_lines = []
                continue
            if code_obj is None:
                # código incompleto -> continuar lendo
                continue
            # temos código pronto para executar
            out, err, exc = None, None, None
            try:
                stdout_buf = io.StringIO()
                stderr_buf = io.StringIO()
                with contextlib.redirect_stdout(stdout_buf):
                    with contextlib.redirect_stderr(stderr_buf):
                        exec(code_obj, self.env, self.env)
                out = stdout_buf.getvalue()
                err = stderr_buf.getvalue()
                if out:
                    print(out, end='')
                if err:
                    print(err, end='', file=sys.stderr)
            except SystemExit:
                raise
            except Exception:
                print(traceback.format_exc())
            buffer_lines = []

# Funções utilitárias para CLI
def executar_arquivo_cli(path):
    interp = LupanInterpreter()
    out, err, exc = interp.executar_arquivo(path)
    if out:
        print(out, end='')
    if err:
        print(err, end='', file=sys.stderr)
    return exc is None

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) >= 1:
        # executar arquivo e sair (comportamento típico)
        executar_arquivo_cli(argv[0])
    else:
        # abrir REPL interativo
        interp = LupanInterpreter()
        interp.repl()

if __name__ == '__main__':
    main()
