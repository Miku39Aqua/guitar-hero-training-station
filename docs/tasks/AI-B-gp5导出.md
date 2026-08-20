# AI-B 任务：IR → gp5 导出器

## 目标
把 `ScoreIR` 对象用 PyGuitarPro 写成 `.gp5` 文件，让用户能在 Guitar Pro 里打开改编后的谱子。

## 背景
项目里已有：
- `tab_engine/ir.py`：谱面中间表示（NoteIR/BeatIR/MeasureIR/ScoreIR）
- `tab_engine/gp_io.py`：已有 SMF→gp5 的读取逻辑（Step 0 验收通过）
- `output/step0_test.gp5`：已验证 PyGuitarPro 能正常写 gp5

你需要新增：**从 ScoreIR 直接构建 gp5 文件**。

## 输入
- `ScoreIR` 对象，字段：
  - `title: str`, `artist: str`, `bpm: int`
  - `time_sig: tuple[int, int]` 如 (4, 4)
  - `tuning: list[int]` 标准调弦 [64, 59, 55, 50, 45, 40]
  - `measures: list[MeasureIR]`
    - `beats: list[BeatIR]`
      - `duration: int`（4=四分, 8=八分, 16=十六分）
      - `notes: list[NoteIR]`
        - `string: int`（1~6，1 是高音 e）
        - `fret: int`（0~24）
        - `technique: str | None`（第一版可忽略）

## 输出
- 函数 `ir_to_gp5(ir: ScoreIR, output_path: str) -> str`
- 返回生成的文件路径
- 文件能被 Guitar Pro 8 正常打开，显示标题/艺术家/BPM/拍号/音符

## 技术要求
1. 用 PyGuitarPro 库（已安装，Step 0 验证过）
2. 参考 `tab_engine/gp_io.py` 里已有的写 gp5 逻辑
3. 注意 PyGuitarPro 的 `Measure`/`Beat`/`Note` 对象构建方式
4. 时值映射：IR 的 4/8/16 → PyGuitarPro 的 `Duration` 枚举
5. 空 `notes` 列表 = 休止符
6. 多音 = 和弦（同一 beat 里多个 Note）

## 验收标准
1. 运行测试脚本 `python scripts/step3_gp5_export_test.py` 通过
2. 生成的 `output/step3_test.gp5` 用 Guitar Pro 8 打开：
   - 标题显示 "gp5 导出测试"
   - 能看到 3 个小节的音符
   - 拍号 4/4，BPM 120

## 文件位置
- 新建 `tab_engine/to_gp5.py`
- 新建测试脚本 `scripts/step3_gp5_export_test.py`

## 提示
- 先读 `tab_engine/ir.py` 和 `tab_engine/gp_io.py` 了解现有结构
- PyGuitarPro 文档：https://pyguitarpro.readthedocs.io/
- 如果 PyGuitarPro 的 API 不确定，先写个小脚本试构建一个最小 gp5
