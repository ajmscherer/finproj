# finproj - v4 section graph (copy and edges, not engine rules)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from model.conditions import goal_is_other
from model.definition import TourDefinition
from model.step import FieldSpec, Step

from gui.v4.content.verbiage import Verbiage

# goal
goal_title = Verbiage(
    {
        "en":"Goal",
        "es":"Objetivo",
        "fr":"Objectif",
        "de":"Ziel",
        "it":"Obiettivo",
        "ja":"目標",
        "pt":"Objetivo",
        "ru":"Цель",
        "zh":"目标",
    }
)
goal_prompt = Verbiage(
    {
    "en":"What is your goal when using this app? Do you want to evaluate when you can retire, or find out how much you need to save to attain a certain lifestyle when you retire, or some other analysis you are interested in?",
    "es":"¿Cuál es tu objetivo al usar esta aplicación? ¿Quieres evaluar cuándo puedes retirarte, o averiguar cuánto necesitas ahorrar para alcanzar un cierto estilo de vida cuando te retires, o alguna otra análisis que te interesan?",
    "fr":"Quel est votre objectif lors de l'utilisation de cette application? Voulez-vous évaluer quand vous pouvez prendre votre retraite, ou découvrir combien vous devez épargner pour atteindre un certain style de vie quand vous prendrez votre retraite, ou quelque autre analyse que vous êtes intéressé?",
    "de":"Was ist Ihr Ziel bei der Verwendung dieser Anwendung? Möchten Sie evaluieren, wann Sie in Rente gehen können, oder herausfinden, wie viel Sie sparen müssen, um ein bestimmtes Leben zu führen, wenn Sie in Rente gehen, oder eine andere Analyse, die Sie interessiert?",
    "it":"Che cosa è il tuo obiettivo quando usi questa app? Vuoi valutare quando puoi andare in pensione, o scoprire quanto devi risparmiare per raggiungere un certo stile di vita quando andrai in pensione, o qualche altra analisi che ti interessa?",
    "ja":"このアプリを使用する目的は何ですか？引退できる時期を評価したいのか、引退後に一定の生活を送るためにどれだけ貯める必要があるかを知りたいのか、それともその他の分析に興味があるのか？",
    "pt":"Qual é o seu objetivo ao usar este aplicativo? Você quer avaliar quando você pode se aposentar, ou descobrir quanto você precisa poupar para atingir um certo estilo de vida quando você se aposentar, ou alguma outra análise que você está interessado?",
    "ru":"Ваше цель при использовании этого приложения? Вы хотите оценить, когда вы сможете выйти на пенсию, или узнать, сколько вам нужно сэкономить, чтобы достичь определенного образа жизни при выходе на пенсию, или какую-то другую аналитику, которая вас интересует?",
    "zh":"你的目标是什么？你想评估何时可以退休，或者想知道为了退休后过上一定的生活需要存多少钱，或者你对其他感兴趣的分析？"
    })

goal_kind_title = Verbiage(
    {
    "en":"What should this projection help you decide?",
    "es":"¿Qué debería ayudarte a decidir esta proyección?",
    "fr":"Qu'est-ce que cette projection devrait vous aider à décider?",
    "de":"Wobei soll diese Projektion Ihnen bei der Entscheidung helfen?",
    "it":"Che cosa dovrebbe aiutarti a decidere questa proiezione?",
    "ja":"この試算は、何を決める助けになるべきですか？",
    "pt":"O que esta projeção deve ajudar você a decidir?",
    "ru":"Что эта проекция должна помочь вам решить?",
    "zh":"这项预测应该帮助你决定什么？"
    })
goal_kind_retire_when = Verbiage(
    {
    "en":"Decide when I can retire",
    "es":"Decidir cuándo puedo jubilarme",
    "fr":"Décider quand je peux prendre ma retraite",
    "de":"Entscheiden, wann ich in Rente gehen kann",
    "it":"Decidere quando posso andare in pensione",
    "ja":"いつ引退できるかを決める",
    "pt":"Decidir quando posso me aposentar",
    "ru":"Решить, когда я смогу выйти на пенсию",
    "zh":"决定我何时可以退休"
    })

goal_kind_save_for_income = Verbiage(
    {
    "en":"Decide how much I need to save",
    "es":"Decidir cuánto necesito ahorrar",
    "fr":"Décider combien je dois épargner",
    "de":"Entscheiden, wie viel ich sparen muss",
    "it":"Decidere quanto devo risparmiare",
    "ja":"どれだけ貯める必要があるかを決める",
    "pt":"Decidir quanto preciso poupar",
    "ru":"Решить, сколько мне нужно накопить",
    "zh":"决定我需要存多少钱"
    })
goal_kind_other = Verbiage(
    {
    "en":"Other usage",
    "es":"Otro uso",
    "fr":"Autre utilisation",
    "de":"Andere Verwendung",
    "it":"Altro utilizzo",
    "ja":"その他の用途",
    "pt":"Outro uso",
    "ru":"Другое применение",
    "zh":"其他用途"
    })
goal_kind_other_help = Verbiage(
    {
    "en":"Pick the usage that best describes what you want to do.",
    "es":"Elige el uso que mejor describe lo que quieres hacer.",
    "fr":"Choisissez l'utilisation qui décrit le mieux ce que vous voulez faire.",
    "de":"Wählen Sie die Verwendung, die am besten beschreibt, was Sie tun möchten.",
    "it":"Scegli l'utilizzo che descrive meglio ciò che vuoi fare.",
    "ja":"やりたいことを最もよく表す用途を選んでください。",
    "pt":"Escolha o uso que melhor descreve o que você quer fazer.",
    "ru":"Выберите вариант, который лучше всего описывает то, что вы хотите сделать.",
    "zh":"请选择最能描述你想做什么的用途。"
    })

wealth_title = Verbiage(
    {
    "en":"Wealth",
    "es":"Riqueza",
    "fr":"Richesse",
    "de":"Vermögen",
    "it":"Patrimonio",
    "ja":"資産",
    "pt":"Patrimônio",
    "ru":"Состояние",
    "zh":"财富"
    })
wealth_prompt = Verbiage(
    {
    "en":"Start with what you have now.",
    "es":"Empieza con lo que tienes ahora.",
    "fr":"Commencez par ce que vous avez maintenant.",
    "de":"Beginnen Sie mit dem, was Sie jetzt haben.",
    "it":"Inizia con ciò che hai ora.",
    "ja":"今持っているものから始めてください。",
    "pt":"Comece com o que você tem agora.",
    "ru":"Начните с того, что у вас есть сейчас.",
    "zh":"从你现在拥有的开始。"
    })
wealth_starting_wealth = Verbiage(
    {
    "en":"Starting wealth",
    "es":"Patrimonio inicial",
    "fr":"Richesse de départ",
    "de":"Anfangsvermögen",
    "it":"Patrimonio iniziale",
    "ja":"初期資産",
    "pt":"Patrimônio inicial",
    "ru":"Начальное состояние",
    "zh":"初始财富"
    })
wealth_starting_wealth_help = Verbiage(
    {
    "en":"You can type 1M for one million, or 250k for 250,000.",
    "es":"Puedes escribir 1M para un millón, o 250k para 250.000.",
    "fr":"Vous pouvez taper 1M pour un million, ou 250k pour 250,000.",
    "de":"Sie können 1M für eine Million eingeben, oder 250k für 250.000.",
    "it":"Puoi digitare 1M per un milione, o 250k per 250,000.",
    "ja":"1Mと入力すると100万、250kと入力すると25万になります。",
    "pt":"Você pode digitar 1M para um milhão, ou 250k para 250,000.",
    "ru":"Можно ввести 1M для миллиона или 250k для 250 000.",
    "zh":"你可以输入1M表示一百万，或者250k表示250,000。"
    })
wealth_cash_buffer = Verbiage(
    {
    "en":"Cash you keep aside",
    "es":"Liquide que vous gardez de côté",
    "fr":"Bargeld, das Sie beiseitelegen",
    "de":"Bargeld, das Sie beiseitelegen",
    "it":"Liquido che tieni da parte",
    "ja":"別に取っておく現金",
    "pt":"Dinheiro que você mantém de lado",
    "ru":"Наличные, которые вы оставляете в стороне",
    "zh":"你另外留出的现金"
    })
wealth_cash_buffer_help = Verbiage(
    {
    "en":"A reserve that is not part of the invested mix.",
    "es":"Una reserva que no forma parte de la mezcla invertida.",
    "fr":"Une réserve qui ne fait pas partie du mélange investi.",
    "de":"Eine Reserve, die nicht zum investierten Mix gehört.",
    "it":"Una riserva che non fa parte del mix investito.",
    "ja":"投資配分に含まれない備えです。",
    "pt":"Uma reserva que não faz parte da combinação investida.",
    "ru":"Резерв, который не входит в инвестиционный набор.",
    "zh":"一笔不属于投资组合的储备。"
    })

# flows
flows_title = Verbiage(
    {
    "en":"In & Out",
    "es":"Entradas y salidas",
    "fr":"Contributions et retraits",
    "de":"Zahlungen und Abhebungen",
    "it":"Entrate e uscite",
    "ja":"入出金",
    "pt":"Entradas e saídas",
    "ru":"Внесенные и снятые средства",
    "zh":"存入和取出"
    })
    
flows_prompt = Verbiage(
    {
    "en":"Yearly amounts. Use 0k if one of them does not apply.",
    "es":"Importes anuales. Usa 0k si alguno no aplica.",
    "fr":"Montants annuels. Utilisez 0k si l'un d'eux ne s'applique pas.",
    "de":"Jährliche Beträge. Verwenden Sie 0k, wenn einer davon nicht zutrifft.",
    "it":"Importi annuali. Usa 0k se uno di essi non si applica.",
    "ja":"年ごとの金額です。当てはまらないものは0kにしてください。",
    "pt":"Quantias anuais. Use 0k se um deles não se aplicar.",
    "ru":"Годовые суммы. Укажите 0k, если что-то из этого не применяется.",
    "zh":"每年的金额。如果其中一项不适用，请填0k。"
    })

flows_contributions = Verbiage(
    {
    "en":"Added each year",
    "es":"Añadido cada año",
    "fr":"Ajouté chaque année",
    "de":"Jährlich hinzugefügt",
    "it":"Aggiunto ogni anno",
    "ja":"毎年追加",
    "pt":"Adicionado anualmente",
    "ru":"Вносится каждый год",
    "zh":"每年存入"
    })
flows_contributions_help = Verbiage(
    {
    "en":"New savings put in every year.",
    "es":"Nuevo ahorro que se aporta cada año.",
    "fr":"Nouvelle épargne versée chaque année.",
    "de":"Neue Ersparnisse, die jedes Jahr eingezahlt werden.",
    "it":"Nuovi risparmi versati ogni anno.",
    "ja":"毎年入れる新しい貯蓄です。",
    "pt":"Novas poupanças colocadas a cada ano.",
    "ru":"Новые сбережения, которые вносятся каждый год.",
    "zh":"每年投入的新储蓄。"
    })
flows_withdrawals = Verbiage(
    {
    "en":"Taken out each year",
    "es":"Retirado cada año",
    "fr":"Retiré chaque année",
    "de":"Jährlich abgezogen",
    "it":"Prelevato ogni anno",
    "ja":"毎年取り出す",
    "pt":"Retirado anualmente",
    "ru":"Снимается каждый год",
    "zh":"每年取出"
    })
flows_withdrawals_help = Verbiage(
    {
    "en":"Spending paid from the portfolio every year.",
    "es":"Gasto pagado con la cartera cada año.",
    "fr":"Dépenses payées du portefeuille chaque année.",
    "de":"Ausgaben aus dem Portfolio jährlich bezahlt",
    "it":"Spese pagate dal portafoglio ogni anno",
    "ja":"毎年ポートフォリオから支払う支出です。",
    "pt":"Despesas pagas do portfólio anualmente",
    "ru":"Расходы, которые каждый год оплачиваются из портфеля.",
    "zh":"每年从投资组合中支付的开支。"
    })

# mix
mix_title = Verbiage(
    {
    "en":"How your money is invested",
    "es":"Cómo está invertido tu dinero",
    "fr":"Comment votre argent est investi",
    "de":"Wie Ihr Geld investiert wird",
    "it":"Come è investito il tuo denaro",
    "ja":"あなたのお金がどのように投資されているか",
    "pt":"Como seu dinheiro é investido",
    "ru":"Как вложены ваши деньги",
    "zh":"你的钱是如何投资的"
    })
mix_prompt = Verbiage(
    {
    "en":"Percentages of the invested mix. They should add up to 100%.",
    "es":"Porcentajes de la mezcla invertida. Deben sumar el 100%.",
    "fr":"Pourcentages du mélange investi. Ils doivent totaliser 100%.",
    "de":"Prozentanteile des investierten Mix. Sie sollten insgesamt 100% ergeben.",
    "it":"Percentuali del mix investito. Devono totalizzare 100%.",
    "ja":"投資配分の割合です。合計が100%になるようにしてください。",
    "pt":"Percentuais da combinação investida. Devem somar 100%.",
    "ru":"Доли инвестиционного набора в процентах. В сумме они должны давать 100%.",
    "zh":"投资组合的百分比。它们应合计为100%。"
    })
mix_money_market = Verbiage(
    {
    "en":"Money market",
    "es":"Mercado monetario",
    "fr":"Marché monétaire",
    "de":"Geldmarkt",
    "it":"Mercato monetario",
    "ja":"マネーマーケット",
    "pt":"Mercado monetário",
    "ru":"Денежный рынок",
    "zh":"货币市场"
    })
mix_bonds = Verbiage(
    {
    "en":"Bonds",
    "es":"Bonos",
    "fr":"Obligations",
    "de":"Anleihen",
    "it":"Obbligazioni",
    "ja":"債券",
    "pt":"Obrigações",
    "ru":"Облигации",
    "zh":"债券"
    })
mix_stocks = Verbiage(
    {
    "en":"Stocks",
    "es":"Acciones",
    "fr":"Actions",
    "de":"Aktien",
    "it":"Azioni",
    "ja":"株式",
    "pt":"Ações",
    "ru":"Акции",
    "zh":"股票"
    })
markets_title = Verbiage(
    {
    "en":"How markets may behave",
    "es":"Cómo pueden comportarse los mercados",
    "fr":"Comment les marchés peuvent se comporter",
    "de":"Wie die Märkte sich verhalten können",
    "it":"Come possono comportarsi i mercati",
    "ja":"市場がどう動くか",
    "pt":"Como os mercados podem se comportar",
    "ru":"Как могут вести себя рынки",
    "zh":"市场可能如何表现"
    })
markets_prompt = Verbiage(
    {
    "en":"Typical yearly growth, and how bumpy the ride is. Not a forecast.",
    "es":"Crecimiento anual típico y cuánto oscila. No es un pronóstico.",
    "fr":"Croissance annuelle typique, et à quel point le parcours est irrégulier. Ce n'est pas une prévision.",
    "de":"Typisches jährliches Wachstum und wie unruhig der Verlauf ist. Keine Prognose.",
    "it":"Crescita annuale tipica e quanto è accidentato il percorso. Non è una previsione.",
    "ja":"典型的な年間の伸びと、どれくらい起伏があるかです。予測ではありません。",
    "pt":"Crescimento anual típico e o quanto o percurso é irregular. Não é uma previsão.",
    "ru":"Типичный годовой рост и насколько неровным будет путь. Это не прогноз.",
    "zh":"典型的年增长，以及过程有多颠簸。这不是预测。"
    })
markets_money_market = Verbiage(
    {
    "en":"Money market growth",
    "es":"Crecimiento del mercado monetario",
    "fr":"Croissance du marché monétaire",
    "de":"Wachstum des Geldmarkts",
    "it":"Crescita del mercato monetario",
    "ja":"マネーマーケットの成長",
    "pt":"Crescimento do mercado monetário",
    "ru":"Рост денежного рынка",
    "zh":"货币市场增长"
    })
markets_money_market_bumpiness = Verbiage(
    {
    "en":"Money market bumpiness",
    "es":"Oscilación del mercado monetario",
    "fr":"Irrégularité du marché monétaire",
    "de":"Unruhe des Geldmarkts",
    "it":"Irregolarità del mercato monetario",
    "ja":"マネーマーケットの起伏",
    "pt":"Irregularidade do mercado monetário",
    "ru":"Неровность денежного рынка",
    "zh":"货币市场颠簸"
    })
markets_bonds = Verbiage(
    {
    "en":"Bonds growth",
    "es":"Crecimiento de los bonos",
    "fr":"Croissance des obligations",
    "de":"Wachstum der Anleihen",
    "it":"Crescita delle obbligazioni",
    "ja":"債券の成長",
    "pt":"Crescimento das obrigações",
    "ru":"Рост облигаций",
    "zh":"债券增长"
    })
markets_bonds_bumpiness = Verbiage(
    {
    "en":"Bonds bumpiness",
    "es":"Oscilación de los bonos",
    "fr":"Irrégularité des obligations",
    "de":"Unruhe der Anleihen",
    "it":"Irregolarità delle obbligazioni",
    "ja":"債券の起伏",
    "pt":"Irregularidade das obrigações",
    "ru":"Неровность облигаций",
    "zh":"债券颠簸"
    })
markets_stocks = Verbiage(
    {
    "en":"Stocks growth",
    "es":"Crecimiento de las acciones",
    "fr":"Croissance des actions",
    "de":"Wachstum der Aktien",
    "it":"Crescita delle azioni",
    "ja":"株式の成長",
    "pt":"Crescimento das ações",
    "ru":"Рост акций",
    "zh":"股票增长"
    })
markets_stocks_bumpiness = Verbiage(
    {
    "en":"Stocks bumpiness",
    "es":"Oscilación de las acciones",
    "fr":"Irrégularité des actions",
    "de":"Unruhe der Aktien",
    "it":"Irregolarità delle azioni",
    "ja":"株式の起伏",
    "pt":"Irregularidade das ações",
    "ru":"Неровность акций",
    "zh":"股票颠簸"
    })

run_title = Verbiage(
    {
    "en":"Run",
    "es":"Ejecutar",
    "fr":"Exécuter",
    "de":"Ausführen",
    "it":"Eseguire",
    "ja":"実行",
    "pt":"Executar",
    "ru":"Запустить",
    "zh":"运行"
    })
run_prompt = Verbiage(
    {
    "en":"How far ahead, and how many possible futures.",
    "es":"Hasta dónde mirar y cuántos futuros posibles.",
    "fr":"Jusqu'où regarder, et combien de futurs possibles.",
    "de":"Wie weit voraus, und wie viele mögliche Zukünfte.",
    "it":"Quanto avanti, e quanti futuri possibili.",
    "ja":"どれだけ先まで見るか、そして可能な未来はいくつか。",
    "pt":"Até onde olhar, e quantos futuros possíveis.",
    "ru":"Насколько далеко вперёд и сколько возможных вариантов будущего.",
    "zh":"向前看多远，以及有多少种可能的未来。"
    })
run_horizon = Verbiage(
    {
    "en":"Years to look ahead",
    "es":"Años por delante",
    "fr":"Années à regarder en avant",
    "de":"Jahre vorausblicken",
    "it":"Anni da guardare avanti",
    "ja":"先を見る年数",
    "pt":"Anos para olhar à frente",
    "ru":"На сколько лет смотреть вперёд",
    "zh":"向前看的年数"
    })
run_nb_projections = Verbiage(
    {
    "en":"Number of futures",
    "es":"Número de futuros",
    "fr":"Nombre de futurs",
    "de":"Anzahl der Zukünfte",
    "it":"Numero di futuri",
    "ja":"可能な未来の数",
    "pt":"Número de futuros",
    "ru":"Число вариантов будущего",
    "zh":"可能的未来数"
    })
run_rng_seed = Verbiage(
    {
    "en":"Random seed",
    "es":"Semilla aleatoria",
    "fr":"Graine aléatoire",
    "de":"Zufälliger Startwert",
    "it":"Seme casuale",
    "ja":"ランダムシード",
    "pt":"Semente aleatória",
    "ru":"Случайное зерно",
    "zh":"随机种子"
    })
review_title = Verbiage(
    {
    "en":"Review",
    "es":"Revisión",
    "fr":"Révision",
    "de":"Überprüfung",
    "it":"Revisione",
    "ja":"確認",
    "pt":"Revisão",
    "ru":"Обзор",
    "zh":"回顾"
    })
review_prompt = Verbiage(
    {
    "en":"Here is what the tour collected. The projection engine is not called yet.",
    "es":"Esto es lo que ha recogido el recorrido. El motor de proyección aún no se ha llamado.",
    "fr":"Voici ce que le parcours a recueilli. Le moteur de projection n'est pas encore appelé.",
    "de":"Hier ist, was der Rundgang gesammelt hat. Die Projektionsengine wird noch nicht aufgerufen.",
    "it":"Ecco che cosa ha raccolto il percorso. Il motore di proiezione non è ancora chiamato.",
    "ja":"ここまでの質問で集めた内容です。試算エンジンはまだ呼び出していません。",
    "pt":"Aqui está o que o percurso recolheu. O motor de projeção ainda não foi chamado.",
    "ru":"Вот что собрал этот обход. Движок проекции ещё не вызывается.",
    "zh":"以下是本次引导收集的内容。预测引擎尚未调用。"
    })


_GOAL_LABELS: dict[str, Verbiage] = {
    "retire_when": goal_kind_retire_when,
    "save_for_income": goal_kind_save_for_income,
    "other": goal_kind_other,
}


def build_definition() -> TourDefinition:
    steps = [
        Step(
            id="goal",
            title=goal_title,
            prompt=goal_prompt,
            fields=[
                FieldSpec(
                    "goal.kind",
                    goal_kind_title,
                    "choice",
                    choices=("retire_when", "save_for_income", "other"),
                    choice_labels=_GOAL_LABELS,
                    help=goal_kind_other_help,
                ),
                FieldSpec(
                    "goal.other_text",
                    goal_kind_other,
                    "text",
                    when=goal_is_other,
                    help=goal_kind_other_help,
                ),
            ],
            default_next="wealth",
            clears_on_change=("goal.other_text",),
        ),
        Step(
            id="wealth",
            title=wealth_title,
            prompt=wealth_prompt,
            fields=[
                FieldSpec(
                    "wealth.initial_capital",
                    wealth_starting_wealth,
                    "amount",
                    help=wealth_starting_wealth_help,
                ),
                FieldSpec(
                    "wealth.cash_buffer",
                    wealth_cash_buffer,
                    "amount",
                    help=wealth_cash_buffer_help,
                ),
            ],
            default_next="flows",
        ),
        Step(
            id="flows",
            title=flows_title,
            prompt=flows_prompt,
            fields=[
                FieldSpec(
                    "flows.contributions",
                    flows_contributions,
                    "amount",
                    help=flows_contributions_help,
                ),
                FieldSpec(
                    "flows.withdrawals",
                    flows_withdrawals,
                    "amount",
                    help=flows_withdrawals_help,
                ),
            ],
            default_next="mix",
        ),
        Step(
            id="mix",
            title=mix_title,
            prompt=mix_prompt,
            fields=[
                FieldSpec(
                    "mix.money_market", mix_money_market, "percent", min=0, max=100
                ),
                FieldSpec("mix.bonds", mix_bonds, "percent", min=0, max=100),
                FieldSpec("mix.stocks", mix_stocks, "percent", min=0, max=100),
            ],
            default_next="markets",
        ),
        Step(
            id="markets",
            title=markets_title,
            prompt=markets_prompt,
            fields=[
                FieldSpec(
                    "markets.money_market.mu",
                    markets_money_market,
                    "percent",
                    min=-20,
                    max=80,
                ),
                FieldSpec(
                    "markets.money_market.sigma",
                    markets_money_market_bumpiness,
                    "percent",
                    min=0,
                    max=100,
                ),
                FieldSpec(
                    "markets.bonds.mu", markets_bonds, "percent", min=-20, max=80
                ),
                FieldSpec(
                    "markets.bonds.sigma",
                    markets_bonds_bumpiness,
                    "percent",
                    min=0,
                    max=100,
                ),
                FieldSpec(
                    "markets.stocks.mu", markets_stocks, "percent", min=-20, max=80
                ),
                FieldSpec(
                    "markets.stocks.sigma",
                    markets_stocks_bumpiness,
                    "percent",
                    min=0,
                    max=100,
                ),
            ],
            default_next="run",
        ),
        Step(
            id="run",
            title=run_title,
            prompt=run_prompt,
            fields=[
                FieldSpec("run.horizon", run_horizon, "int", min=1, max=50),
                FieldSpec(
                    "run.nb_projections",
                    run_nb_projections,
                    "int",
                    min=10,
                    max=20000,
                ),
                FieldSpec("run.rng_seed", run_rng_seed, "int", min=1),
            ],
            default_next="review",
        ),
        Step(
            id="review",
            title=review_title,
            prompt=review_prompt,
            fields=[],
        ),
    ]
    return TourDefinition(steps, start="goal")
