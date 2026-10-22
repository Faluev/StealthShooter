# Перечисления, таблицы данных, время и практическая 1.9

## Применение уроков

`E_LightColor` содержит Red, Yellow и Green. Switch on E_LightColor в ScheduleNext выбирает длительность состояния. Enum применяется к светофорам из заготовки, поэтому новый тип для бонусов не дублируется.

`DT_TrafficSettings` использует исходную структуру `S_LIghtColor` и содержит три строки: Default, LowBrightness и HighVisibility. Настройка SettingsRow — Data Table Row Handle; LoadSettings получает строку, проверяет результат и переносит данные в ColorSettings. При отсутствии строки остаётся структура экземпляра. В таблице сохранены соответствия Green/Yellow/Red и LinearColor. На учебной карте BP_DataTableExamples получает имена всех строк через Get Data Table Row Names и обходит их через ForEach с чтением типизированных данных.

В `BP_TimingExamples` Sequence запускает Delay на 3 секунды и сразу продолжает другую ветвь. PrintHello вызывается повторяющимся таймером каждые 2 секунды. События StartNormalDelay и StartRetriggerDelay позволяют сравнить повторный вызов обычной и перезапускаемой задержки на 1 секунду. В отличие от формулировки учебного PDF, ожидание не создаёт отдельный поток операционной системы: продолжение откладывается до последующих кадров игрового потока.

## Практическая 1.9

Сохранены архитектура и ресурсы учебной заготовки. При Begin Play менеджер ждёт 0,2 секунды для инициализации динамических материалов, читает настройки, собирает четыре BP_TraffictLight и запускает Recolor. Дальнейшее переключение выполняют одноразовые таймеры.

Recolor выбирает ключ по индексу, получает цвет из Map, обходит Lights через ForEach и вызывает исходный ChangeColor. Ключи ColorSettings сохраняются в ColorOrder один раз, и цикл повторяет эту последовательность. Для строки Default это Green → Yellow → Red. Пустая последовательность останавливает цикл; отсутствующая ссылка на светофор пропускается через Is Valid.

В заготовке ChangeColor принимает LinearColor и меняет параметр динамического материала. Именно этот интерфейс сохранён, хотя текст задания называет вход материалом. Новые акторы светофоров используют исходный Blueprint и его сферический меш.

Обязательный режим — одинаковый интервал 2 секунды. Дополнительный VariableIntervals — красный 5, жёлтый 1, зелёный 3 секунды. Независимые фазы двух направлений перекрёстка не реализованы: это второй необязательный вариант задания.

У старой карты были фиксированные нулевые границы экспозиции, которые давали белый экран после переноса. Для UE 5.8 обе границы установлены в 1; механика персонажа и геометрия заготовки сохранены. Комментарии добавлены к графам менеджера и демонстрации времени.

## Проверки

- [Структуры и контейнеры: 38 проверок](Lessons13-15Validation.json).
- [Delay, Retriggerable Delay и повторяющийся Timer](TimingValidation.json).
- [Реальные изменения материалов и интервалы светофоров](TrafficLightsValidation.json).
- [Три строки Data Table и обработка отсутствующей строки](DataTableValidation.json).
- [Компиляция всех 15 Blueprint и AnimBlueprint проекта](CompilationValidation.json).

Проверки выполняются в Play In Editor по фактическим значениям объектов и материалов, с ожиданием между кадрами. Скрипты находятся в Tools. Исходная предыдущая игра в этот проект не входит и не изменяется.

## Материалы курса

- [1.6 Enumeration](https://go.skillbox.ru/profession/profession-unreal-engine-5-game-developer-from-scratch/game-stels-shuter/longread/ab7f0a43-5fb9-4f3e-a457-276b7acb3e69)
- [1.7 Data Tables](https://go.skillbox.ru/profession/profession-unreal-engine-5-game-developer-from-scratch/game-stels-shuter/longread/7e794073-6351-42df-a9a1-82f710951eca)
- [1.8 Delay и Timer](https://go.skillbox.ru/profession/profession-unreal-engine-5-game-developer-from-scratch/game-stels-shuter/videolesson/358c9e7c-14b8-4a7d-b957-d66dfaab4541)
- [1.9 Практическая работа](https://go.skillbox.ru/profession/profession-unreal-engine-5-game-developer-from-scratch/game-stels-shuter/homework/b8830c65-1dda-4d07-bb47-f0f508eb8f7a)
