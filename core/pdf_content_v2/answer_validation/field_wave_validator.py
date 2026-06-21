"""Field wave answer validator (placeholder architecture)."""

from core.pdf_content_v2.answer_validation.answer_validator import AnswerValidator, ValidationResult


class FieldWaveValidator(AnswerValidator):
    """Validate EM field answers: units, directions, boundary conditions, etc.

    Checks (to be implemented with seed data):
        1. Units: E in V/m, D in C/m², φ in V
        2. Direction: vector notation presence
        3. Gaussian surface applicability conditions
        4. Boundary conditions: tangential E continuous, normal D jump = ρₛ
        5. E = -∇φ relationship
        6. Image method applicability conditions
    """

    def validate(self, question: dict) -> ValidationResult:
        problem = str(question.get("problem", question.get("stem", "")))
        answer = str(question.get("answer", question.get("standard_answer", "")))

        # Check for vector awareness in EM answers
        if "电场" in problem or "场强" in problem:
            if "方向" not in answer and "R̂" not in answer and "矢量" not in answer:
                return ValidationResult(is_valid=True, confidence=0.5,
                    message="电场答案建议包含方向信息")

        # Check boundary condition terminology
        if "边界" in problem:
            if "切向" not in answer and "法向" not in answer and "连续" not in answer:
                return ValidationResult(is_valid=True, confidence=0.5,
                    message="边界条件答案建议明确切向/法向")

        # Check unit awareness
        if any(unit in answer for unit in ["V/m", "C/m²", "V", "N/C"]):
            return ValidationResult(is_valid=True, confidence=0.8,
                message="答案包含正确物理单位")

        return ValidationResult(is_valid=True, confidence=0.5,
            message="场波答案格式检查通过（未深度验证）")
