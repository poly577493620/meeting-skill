#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要结构校验脚本

功能：
  对生成的会议纪要 Markdown 文件进行确定性的结构和疑似泄露检查。

使用方式：
  python scripts/check_minutes.py <会议纪要Markdown文件路径>

检查项目：
  1. 输入文件是否存在且为 Markdown 文件。
  2. 是否包含六个固定部分：会议基本信息、会议讨论、明确决议、行动项、未明确事项、脱敏说明。
  3. 行动项表格是否包含六个必需列：编号、行动事项、责任人、协同方、截止时间、交付物/验收点。
  4. 行动项字段不得直接留空；信息缺失时必须填写"未明确"。
  5. 行动项字段不得使用禁用占位词（待定/TBD/暂无/不适用）替代"未明确"。
  6. 是否出现疑似精确小数金额（未呈现为完整区间），提示需进一步人工检查。
  7. 是否缺少客户姓名脱敏标记、金额区间化说明或项目代号脱敏说明。

重要说明：
  本脚本只能做确定性的格式和疑似泄露检查，无法判断模型是否编造事实。
  事实准确性仍需根据原始转写文本人工复核。
  脚本不会在终端中回显完整会议纪要或原始敏感行，只输出问题类型和所在检查项目编号，
  不输出文件中的具体敏感内容，避免在错误信息中泄露敏感原文。

退出码：
  0 - 校验通过
  1 - 校验失败（存在一个或多个问题）
  2 - 参数错误或文件不可读
"""

import sys
import os
import re


# 六个固定部分（按出现顺序）
REQUIRED_SECTIONS = [
    '会议基本信息',
    '会议讨论',
    '明确决议',
    '行动项',
    '未明确事项',
    '脱敏说明',
]

# 行动项表格六个必需列
REQUIRED_COLUMNS = [
    '编号',
    '行动事项',
    '责任人',
    '协同方',
    '截止时间',
    '交付物/验收点',
]

# 疑似精确小数金额的正则模式
# 匹配带小数的金额，如 2.5亿元、1.23亿、5000.5万 等。
SUSPICIOUS_AMOUNT_PATTERN = re.compile(
    r'(\d+)\.(\d+)\s*(亿|万)',
)

# 合理区间模式：形如 2—3亿、4000万—6000万元、1—2亿元、1.5亿—2.5亿 等。
# 范围界定内的金额（含小数边界的区间）属于区间化表达，不作为精确泄漏。
# 分隔符兼容中文破折号、半角/全角连字符、波浪号及汉字"至/到"。
RANGE_AMOUNT_PATTERN = re.compile(
    r'\d+(?:\.\d+)?\s*(?:亿|万)?\s*[—–‒\-~至到]\s*\d+(?:\.\d+)?\s*(亿|万)'
)


def check_file_exists(filepath):
    """检查文件是否存在且为 Markdown 文件。"""
    issues = []
    if not os.path.isfile(filepath):
        issues.append('文件不存在：{}'.format(filepath))
        return issues, None
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ('.md', '.markdown'):
        issues.append('文件不是 Markdown 文件（扩展名：{}）'.format(ext))
    return issues, filepath


def read_file(filepath):
    """读取文件内容，返回行列表。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()


def check_required_sections(lines):
    """检查是否包含六个固定部分。"""
    issues = []
    full_text = '\n'.join(lines)
    for section in REQUIRED_SECTIONS:
        # 检查是否作为标题出现（## 或 ### 级别）
        pattern = re.compile(r'^#{1,4}\s+' + re.escape(section), re.MULTILINE)
        if not pattern.search(full_text):
            issues.append('缺少固定部分：{}'.format(section))
    return issues


def find_table_block(lines):
    """
    找到行动项表格区域。
    返回表格行列表（含表头、分隔行、数据行）。
    """
    table_lines = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and '编号' in stripped and '行动事项' in stripped:
            in_table = True
            table_lines.append(stripped)
            continue
        if in_table:
            if stripped.startswith('|'):
                table_lines.append(stripped)
            elif stripped == '':
                # 空行表示表格结束
                break
            else:
                break
    return table_lines


def check_table_columns(table_lines):
    """检查行动项表格是否包含六个必需列。"""
    issues = []
    if not table_lines:
        issues.append('未找到行动项表格（缺少包含[编号]和[行动事项]的表格行）')
        return issues

    # 第一行是表头
    header = table_lines[0]
    header_cells = [cell.strip() for cell in header.split('|')]
    # 去掉首尾空字符串（由首尾 | 产生）
    header_cells = [c for c in header_cells if c != '']

    for col in REQUIRED_COLUMNS:
        found = False
        for cell in header_cells:
            if col in cell:
                found = True
                break
        if not found:
            issues.append('行动项表格缺少必需列：{}'.format(col))

    return issues


# 行动项表格中禁止用作"未明确"替代词的占位词
FORBIDDEN_PLACEHOLDERS = ['待定', 'tbd', '暂无', '不适用', '待补充', '待确认']

# 行动项表格六个必需列（按顺序）。校验列顺序以与规范保持一致。
def check_table_empty_cells(table_lines):
    """检查行动项数据行中是否有直接留空的单元格。"""
    issues = []
    if len(table_lines) < 3:
        # 至少需要表头 + 分隔行 + 1 行数据
        return issues

    # 数据行从第 3 行开始（索引 2）
    for i, line in enumerate(table_lines[2:], start=1):
        raw_cells = line.split('|')
        # 去掉首尾由 | 产生的空字符串
        if raw_cells and raw_cells[0] == '':
            raw_cells = raw_cells[1:]
        if raw_cells and raw_cells[-1] == '':
            raw_cells = raw_cells[:-1]

        for j, cell in enumerate(raw_cells):
            cell_stripped = cell.strip()
            if cell_stripped == '':
                issues.append(
                    '行动项第 {} 行第 {} 列单元格为空，缺失信息应填写"未明确"'.format(i, j + 1)
                )

    # 检查禁用占位词（仅指明行列，不回显单元格内容）
    for i, line in enumerate(table_lines[2:], start=1):
        raw_cells = line.split('|')
        if raw_cells and raw_cells[0] == '':
            raw_cells = raw_cells[1:]
        if raw_cells and raw_cells[-1] == '':
            raw_cells = raw_cells[:-1]
        for j, cell in enumerate(raw_cells):
            cell_lower = cell.strip().lower()
            for ph in FORBIDDEN_PLACEHOLDERS:
                if ph in cell_lower:
                    issues.append(
                        '行动项第 {} 行第 {} 列使用了禁用占位词（{}），缺失信息应填写"未明确"'.format(
                            i, j + 1, ph.upper()
                        )
                    )
    return issues


def check_suspicious_amounts(lines):
    """
    检查是否出现疑似精确小数金额。
    呈现为完整区间（X—Y亿/万）的金额视为已区间化，不作为精确泄漏。
    处理逻辑：先在全文中划出区间片段，对位于区间内的金额不作告警；
    仅对未处于任何区间内的"带小数点的精确金额"提示人工复核。
    """
    issues = []
    full_text = '\n'.join(lines)

    # 收集所有区间片段的起止位置，供后续排除使用。
    range_spans = [m.span() for m in RANGE_AMOUNT_PATTERN.finditer(full_text)]

    def in_any_range(pos):
        for start, end in range_spans:
            if start <= pos < end:
                return True
        return False

    suspicious = False
    for m in SUSPICIOUS_AMOUNT_PATTERN.finditer(full_text):
        if not in_any_range(m.start()):
            suspicious = True
            break

    if suspicious:
        issues.append(
            '发现疑似精确小数金额表达（未呈现为完整区间的带小数金额），需人工确认是否已完成区间化脱敏'
        )
    return issues


def check_redaction_markers(lines):
    """检查脱敏说明部分是否覆盖客户姓名、金额、项目代号三类。不回显文件内容。"""
    issues = []

    # 检查脱敏说明部分是否存在
    desensitization_section_found = False
    for line in lines:
        if '脱敏说明' in line and line.strip().startswith('#'):
            desensitization_section_found = True
            break

    if not desensitization_section_found:
        issues.append('脱敏说明部分缺失，无法确认脱敏处理情况')
        return issues

    # 获取脱敏说明部分之后的内容（直到下一个同级或更高级标题）
    desensitization_content = []
    found_section = False
    for line in lines:
        if '脱敏说明' in line and line.strip().startswith('#'):
            found_section = True
            continue
        if found_section:
            if line.strip().startswith('#') and '脱敏说明' not in line:
                break
            desensitization_content.append(line)

    desensitization_text = '\n'.join(desensitization_content)

    missing_keywords = ['客户姓名', '金额', '项目代号']
    missing_messages = [
        '脱敏说明中缺少客户姓名脱敏处理说明',
        '脱敏说明中缺少敏感金额区间化说明',
        '脱敏说明中缺少秘密项目代号脱敏说明',
    ]
    present_tokens = [
        ['[客户姓名已脱敏]', '客户姓名'],
        ['区间', '金额'],
        ['******', '项目代号'],
    ]
    for kw, msg, tokens in zip(missing_keywords, missing_messages, present_tokens):
        if not any(tok in desensitization_text for tok in tokens):
            issues.append(msg)
    return issues


def main():
    if len(sys.argv) != 2:
        print('用法：python scripts/check_minutes.py <会议纪要Markdown文件路径>')
        sys.exit(2)

    filepath = sys.argv[1]

    # 检查 1：文件是否存在且为 Markdown 文件
    file_issues, valid_path = check_file_exists(filepath)
    if file_issues:
        for issue in file_issues:
            print('FAIL：{}'.format(issue))
        sys.exit(2)

    lines = read_file(valid_path)

    all_issues = []

    # 检查 2：六个固定部分
    all_issues.extend(check_required_sections(lines))

    # 检查 3、4、5：行动项表格列、空单元格及禁用占位词
    table_lines = find_table_block(lines)
    all_issues.extend(check_table_columns(table_lines))
    all_issues.extend(check_table_empty_cells(table_lines))

    # 检查 6：疑似精确小数金额
    all_issues.extend(check_suspicious_amounts(lines))

    # 检查 7：脱敏说明覆盖
    all_issues.extend(check_redaction_markers(lines))

    # 输出结果
    if all_issues:
        for issue in all_issues:
            print('FAIL：{}'.format(issue))
        sys.exit(1)
    else:
        print('PASS：会议纪要结构检查通过。')
        sys.exit(0)


if __name__ == '__main__':
    main()
