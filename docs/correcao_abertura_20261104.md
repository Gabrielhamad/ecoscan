# Correção de abertura do Streamlit — 04/11/2026

A tela inicial consultava campanhas antes da identificação e calculava abas de
dados ocultas. Também importava motores de imagem e treinamento antes de existir
uma foto. Isso aumentava o trabalho de abertura e fazia a entrada depender de
serviços que poderiam estar lentos.

A correção carrega dados das abas selecionadas, mantém a captura montada para
preservar a foto e adia motores de imagem até o uso. O diretório de contas só
consulta o Auth quando aberto. A entrada `streamlit_app.py` mostra progresso
antes de importar funcionalidades e apresenta nova tentativa em falha de importação.

As requisições Supabase usam limites de inatividade por fase: conexão/fila de
3 segundos, leitura/escrita de 8 segundos. Isso não é um prazo total por página.
Falhas temporárias do Auth preservam o token para nova tentativa, mas bloqueiam
conteúdo autenticado até nova verificação. Tokens inválidos continuam sendo
removidos. Não há cache global de credenciais nem repetição automática de gravações.

Validação da versão isolada: 524 testes e 100 subtestes aprovados; diagnóstico
local com zero falhas. A primeira página também foi testada com importações de
OpenCV, SciPy, scikit-learn, PyTorch e ONNX Runtime bloqueadas. Testes verificam
recuperação do login, isolamento de clientes e ausência de consultas de abas ocultas.

Streamlit mínimo: 1.66, declarado nos dois arquivos de dependências. O launcher
local e a hospedagem usam a mesma entrada. Não há alteração nos pesos de reconhecimento.

A resposta do site público e os logs do Streamlit Community Cloud não puderam ser
consultados neste ambiente por restrição de rede. O envio de código não comprova
que o deploy terminou. Se a hospedagem estiver suspensa, a reativação ainda tem
latência; uma instância sempre ativa é necessária para evitar essa espera.
