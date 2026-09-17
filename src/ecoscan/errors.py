from __future__ import annotations

from dataclasses import asdict, dataclass

from ecoscan.classification.inference import ModelLoadError
from ecoscan.config import ConfigError
from ecoscan.disposal.guidance import GuidanceError
from ecoscan.image_processing.filters import FilterUnavailableError
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.segmentation.methods import SegmentationUnavailableError
from ecoscan.services.dataset_ingestion import DatasetIngestionError
from ecoscan.training.transfer_learning import TrainingEnvironmentError


@dataclass(frozen=True)
class EcoScanUserError:
    code: str
    title: str
    message: str
    action: str
    technical_detail: str
    category: str

    def public_payload(self, *, include_technical: bool = False) -> dict[str, str | bool]:
        payload: dict[str, str | bool] = {
            "ok": False,
            "code": self.code,
            "title": self.title,
            "error": self.message,
            "message": self.message,
            "action": self.action,
            "category": self.category,
        }
        if include_technical:
            payload["technical_detail"] = self.technical_detail
        return payload


@dataclass(frozen=True)
class _ErrorTemplate:
    code: str
    title: str
    message: str
    action: str
    category: str


_TEMPLATES: tuple[tuple[type[BaseException], _ErrorTemplate], ...] = (
    (
        ImageValidationError,
        _ErrorTemplate(
            "IMG-001",
            "Imagem inválida",
            "A imagem enviada não pôde ser validada pelo EcoScan.",
            "Use uma imagem JPG, JPEG ou PNG legível, com boa resolução e um resíduo principal visível.",
            "image",
        ),
    ),
    (
        ModelLoadError,
        _ErrorTemplate(
            "MODEL-001",
            "Modelo indisponível",
            "O modelo necessário para reconhecimento não pôde ser carregado.",
            "Treine a baseline ou o modelo final antes de rodar a inferência.",
            "model",
        ),
    ),
    (
        FilterUnavailableError,
        _ErrorTemplate(
            "PROC-001",
            "Filtro indisponível",
            "O filtro selecionado depende de uma biblioteca que não está disponível neste ambiente.",
            "Instale as dependências opcionais ou escolha outro filtro no painel de processamento.",
            "processing",
        ),
    ),
    (
        SegmentationUnavailableError,
        _ErrorTemplate(
            "SEG-001",
            "Segmentação indisponível",
            "O método de segmentação selecionado depende de uma biblioteca que não está disponível neste ambiente.",
            "Instale as dependências opcionais ou escolha Otsu/sem segmentação.",
            "segmentation",
        ),
    ),
    (
        TrainingEnvironmentError,
        _ErrorTemplate(
            "TRAIN-001",
            "Ambiente de treino incompleto",
            "O ambiente atual não está pronto para treinar o modelo final.",
            "Use um ambiente com TensorFlow instalado, preferencialmente Python 3.12, e rode novamente após curar o dataset.",
            "training",
        ),
    ),
    (
        DatasetIngestionError,
        _ErrorTemplate(
            "DATA-001",
            "Entrada de dataset inválida",
            "O lote não pôde ser salvo no dataset bruto.",
            "Confira a classe de destino e envie apenas arquivos de imagem aceitos pelo projeto.",
            "dataset",
        ),
    ),
    (
        ConfigError,
        _ErrorTemplate(
            "CFG-001",
            "Configuração inválida",
            "A configuração do EcoScan não pôde ser carregada corretamente.",
            "Revise config/settings.json antes de executar a aplicação.",
            "configuration",
        ),
    ),
    (
        GuidanceError,
        _ErrorTemplate(
            "GUIDE-001",
            "Orientação ambiental ausente",
            "A classe reconhecida não possui orientação de descarte configurada.",
            "Revise config/disposal_guidance.json e cadastre a orientação da classe.",
            "guidance",
        ),
    ),
    (
        PermissionError,
        _ErrorTemplate(
            "IO-002",
            "Permissão negada",
            "O EcoScan não conseguiu acessar ou gravar um arquivo necessário.",
            "Verifique se a pasta do projeto está liberada e se nenhum arquivo está bloqueado por outro programa.",
            "io",
        ),
    ),
    (
        FileNotFoundError,
        _ErrorTemplate(
            "IO-001",
            "Arquivo não encontrado",
            "Um arquivo necessário não foi encontrado.",
            "Confira se os scripts foram executados na pasta do projeto e se os caminhos existem.",
            "io",
        ),
    ),
    (
        ValueError,
        _ErrorTemplate(
            "APP-002",
            "Entrada inválida",
            "Um parâmetro informado não é aceito pelo EcoScan.",
            "Revise as opções escolhidas e tente novamente.",
            "application",
        ),
    ),
)


def describe_exception(exc: BaseException) -> EcoScanUserError:
    technical_detail = _technical_detail(exc)
    for exception_type, template in _TEMPLATES:
        if isinstance(exc, exception_type):
            return EcoScanUserError(
                code=template.code,
                title=template.title,
                message=template.message,
                action=template.action,
                technical_detail=technical_detail,
                category=template.category,
            )

    return EcoScanUserError(
        code="APP-001",
        title="Falha inesperada",
        message="O EcoScan encontrou uma falha inesperada durante a operação.",
        action="Tente novamente e consulte o log técnico em logs/ecoscan.log se o problema persistir.",
        technical_detail=technical_detail,
        category="application",
    )


def public_error_payload(exc: BaseException, *, include_technical: bool = False) -> dict[str, str | bool]:
    return describe_exception(exc).public_payload(include_technical=include_technical)


def format_console_error(exc: BaseException) -> str:
    error = describe_exception(exc)
    lines = [
        f"{error.code} - {error.title}",
        error.message,
        f"Ação recomendada: {error.action}",
    ]
    if error.technical_detail:
        lines.append(f"Detalhe técnico: {error.technical_detail}")
    return "\n".join(lines)


def format_error_payload_for_console(payload: dict[str, str | bool]) -> str:
    lines = [
        f"{payload.get('code')} - {payload.get('title')}",
        str(payload.get("message") or payload.get("error") or ""),
        f"Ação recomendada: {payload.get('action')}",
    ]
    detail = payload.get("technical_detail")
    if detail:
        lines.append(f"Detalhe técnico: {detail}")
    return "\n".join(lines)


def error_catalog() -> tuple[EcoScanUserError, ...]:
    items = [
        EcoScanUserError(
            code=template.code,
            title=template.title,
            message=template.message,
            action=template.action,
            technical_detail="",
            category=template.category,
        )
        for _, template in _TEMPLATES
    ]
    items.extend(
        [
            EcoScanUserError(
                "CAM-001",
                "Frame vazio",
                "A câmera não enviou imagem para análise.",
                "Mantenha a câmera ativa e tente capturar o frame novamente.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-002",
                "Frame muito grande",
                "O frame enviado excede o limite aceito pelo EcoScan Live.",
                "Reduza a resolução da câmera ou atualize a página para usar a captura compactada.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-003",
                "Cabeçalho inválido",
                "O tamanho do frame enviado pela câmera é inválido.",
                "Atualize a página e tente iniciar a câmera novamente.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-004",
                "Frame incompleto",
                "A câmera enviou um frame incompleto para análise.",
                "Verifique a conexão do navegador e tente novamente.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-005",
                "OpenCV ausente",
                "A captura direta por webcam precisa da biblioteca opencv-python.",
                "Instale opencv-python ou use a câmera do navegador pela interface Streamlit.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-006",
                "Webcam indisponível",
                "A câmera solicitada não foi encontrada ou está sem permissão.",
                "Confira a permissão da câmera, feche aplicativos que possam estar usando a webcam ou teste outro índice.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "CAM-007",
                "Captura falhou",
                "A webcam abriu, mas não retornou um frame válido.",
                "Tente novamente com boa iluminação ou reinicie a câmera.",
                "",
                "camera",
            ),
            EcoScanUserError(
                "HTTP-404",
                "Rota não encontrada",
                "A rota solicitada não existe no EcoScan Live.",
                "Abra a página inicial do EcoScan Live ou use a rota correta da API.",
                "",
                "http",
            ),
        ]
    )
    return tuple(sorted(items, key=lambda item: item.code))


def build_error_payload(
    *,
    code: str,
    title: str,
    message: str,
    action: str,
    category: str,
    technical_detail: str = "",
    include_technical: bool = False,
) -> dict[str, str | bool]:
    error = EcoScanUserError(
        code=code,
        title=title,
        message=message,
        action=action,
        technical_detail=technical_detail,
        category=category,
    )
    return error.public_payload(include_technical=include_technical)


def as_log_fields(error: EcoScanUserError) -> dict[str, str]:
    return {key: str(value) for key, value in asdict(error).items()}


def _technical_detail(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__
