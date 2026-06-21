"""Course Plugin Architecture — generic course interface for PDF 5.0.

All course differences MUST come from plugins. No if/else on course name anywhere.
"""

from core.course_plugins.base_plugin import BaseCoursePlugin
from core.course_plugins.generic_plugin import GenericCoursePlugin
from core.course_plugins.course_isolation import CourseIsolationSandbox, IsolationReport
from core.course_plugins.option_answer_validator import OptionAnswerConsistencyValidator
from core.course_plugins.solution_concrete_validator import SolutionConcreteValidator
from core.course_plugins.plugin_registry import (
    CoursePluginRegistry,
    CourseNotSupportedError,
    get_plugin_registry,
    get_plugin,
)
