# Copyright (c) 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from sunbeam.jobs.questions import QuestionBank


def show_questions(
    question_bank: QuestionBank,
    section: str | None = None,
    subsection: str | None = None,
    section_description: str | None = None,
    comment_out: bool = False,
) -> list[str]:
    """Return preseed questions as list."""
    lines = []
    space = " "
    indent = ""
    outer_indent = space * 2
    if comment_out:
        comment = "# "
    else:
        comment = ""
    if section:
        if section_description:
            lines.append(
                f"{outer_indent}{comment}{indent}# {section_description}"
            )
        lines.append(f"{outer_indent}{comment}{indent}{section}:")
        indent = space * 2
    if subsection:
        lines.append(f"{outer_indent}{comment}{indent}{subsection}:")
        indent = space * 4
    for key, question in question_bank.questions.items():
        default = question.calculate_default() or ""
        lines.append(f"{outer_indent}{comment}{indent}# {question.question}")
        lines.append(f'{outer_indent}{comment}{indent}{key}: "{default}"')

    return lines
