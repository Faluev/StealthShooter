# StealthShooter — продвинутые Blueprint

Учебный проект Unreal Engine 5.8.3 для модуля «Продвинутые Blueprint. Часть 1». Примеры уроков и практическая работа находятся в одном проекте.

## Запуск

1. Клонируйте репозиторий с установленным Git LFS и выполните `git lfs pull`.
2. Откройте `StealthShooter.uproject` в Unreal Engine 5.8.3.
3. На карте `ThirdPersonMap` нажмите Play: четыре светофора циклически меняют цвет Green → Yellow → Red с интервалом 2 секунды.
4. WASD — движение, мышь — обзор, пробел — прыжок. Esc завершает Play In Editor.

В экземпляре `BP_TrafficLightsManager` параметр `VariableIntervals` включает дополнительный режим: зелёный 3 секунды, жёлтый 1, красный 5. Меняйте параметры перед запуском Play. `SettingsRow` выбирает строку из `DT_TrafficSettings`, а `ColorSettings` хранит рабочую структуру с Map цветов.

![Практическая работа в Play](Docs/Screenshots/TrafficLightsPlay.jpg)

Карта `Content/StealthShooter/Maps/L_BlueprintLab` содержит отдельные демонстрации структур, Array, Set, Map, ForEach, Break, Delay и таймеров. Это основа следующих этапов курса; игровая логика полноценного стелс-шутера пока не реализована.

## Реализовано

- **1.3–1.5:** Make/Break/Set Members структуры, выбор меша из структуры, обход контейнеров и досрочное завершение цикла. [Описание и проверки](Docs/Lessons13-15.md).
- **1.6–1.8:** Enumeration и Switch, Data Table и Row Handle, Delay, Retriggerable Delay, повторяющийся и одноразовый Timer. [Описание](Docs/Lessons16-19.md).
- **1.9:** `BP_TrafficLightsManager.Recolor` читает ColorSettings и вызывает существующий ChangeColor у каждого светофора; таймер повторяет цикл без Tick. Добавлен режим с разными длительностями.

Инструменты редактирования включаются только через `Tools/OpenStealthEditor.ps1 -WithTools`. Для обычного просмотра готовых Blueprint они не нужны. Бинарные ресурсы находятся в Git LFS, временные данные и сборки исключены через `.gitignore`.

Проект использует предоставленную учебную заготовку и ресурсы Third Person от Epic Games. [Происхождение ресурсов](NOTICE.md).
