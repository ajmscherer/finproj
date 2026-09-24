# finproj - v4 section graph (copy and edges, not engine rules)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from model.conditions import goal_is_other
from model.definition import TourDefinition
from model.step import FieldSpec, Step

from gui.v4.content.verbiage import Verbiage

# goal
goal_title = Verbiage(
    "Your goal[en]|Tu objetivo[es]|Votre objectif[fr]|Ihr Ziel[de]|Il tuo obiettivo[it]|目標[ja]|Seu objetivo[pt]|Ваша цель[ru]|你的目标[zh]"
)
goal_prompt = Verbiage(
    "How would you like to use this app?[en]|¿Cómo te gustaría usar esta aplicación?[es]|Comment aimeriez-vous utiliser cette application?[fr]|Wie möchten Sie diese Anwendung nutzen?[de]|Come vorresti utilizzare questa applicazione?[it]|このアプリをどのように使いたいですか？[ja]|Como você gostaria de usar este aplicativo?[pt]|Как бы вы хотели пользоваться этим приложением?[ru]|你希望如何使用这个应用程序？[zh]"
)
goal_kind_title = Verbiage(
    "What should this projection help you decide?[en]|¿Qué debería ayudarte a decidir esta proyección?[es]|Qu'est-ce que cette projection devrait vous aider à décider?[fr]|Wobei soll diese Projektion Ihnen bei der Entscheidung helfen?[de]|Che cosa dovrebbe aiutarti a decidere questa proiezione?[it]|この試算は、何を決める助けになるべきですか？[ja]|O que esta projeção deve ajudar você a decidir?[pt]|Что эта проекция должна помочь вам решить?[ru]|这项预测应该帮助你决定什么？[zh]"
)
goal_kind_retire_when = Verbiage(
    "Decide when I can retire[en]|Decidir cuándo puedo jubilarme[es]|Décider quand je peux prendre ma retraite[fr]|Entscheiden, wann ich in Rente gehen kann[de]|Decidere quando posso andare in pensione[it]|いつ引退できるかを決める[ja]|Decidir quando posso me aposentar[pt]|Решить, когда я смогу выйти на пенсию[ru]|决定我何时可以退休[zh]"
)
goal_kind_save_for_income = Verbiage(
    "Decide how much I need to save [en]|Decidir cuánto necesito ahorrar[es]|Décider combien je dois épargner[fr]|Entscheiden, wie viel ich sparen muss[de]|Decidere quanto devo risparmiare[it]|どれだけ貯める必要があるかを決める[ja]|Decidir quanto preciso poupar[pt]|Решить, сколько мне нужно накопить[ru]|决定我需要存多少钱[zh]"
)
goal_kind_other = Verbiage(
    "Other usage[en]|Otro uso[es]|Autre utilisation[fr]|Andere Verwendung[de]|Altro utilizzo[it]|その他の用途[ja]|Outro uso[pt]|Другое применение[ru]|其他用途[zh]"
)
goal_kind_other_help = Verbiage(
    "Pick the usage that best describes what you want to do.[en]|Elige el uso que mejor describe lo que quieres hacer.[es]|Choisissez l'utilisation qui décrit le mieux ce que vous voulez faire.[fr]|Wählen Sie die Verwendung, die am besten beschreibt, was Sie tun möchten.[de]|Scegli l'utilizzo che descrive meglio ciò che vuoi fare.[it]|やりたいことを最もよく表す用途を選んでください。[ja]|Escolha o uso que melhor descreve o que você quer fazer.[pt]|Выберите вариант, который лучше всего описывает то, что вы хотите сделать.[ru]|请选择最能描述你想做什么的用途。[zh]"
)

wealth_title = Verbiage(
    "Your Wealth[en]|Tu riqueza[es]|Votre richesse[fr]|Ihr Vermögen[de]|Il tuo patrimonio[it]|あなたの資産[ja]|Seu patrimônio[pt]|Ваше состояние[ru]|你的财富[zh]"
)
wealth_prompt = Verbiage(
    "Start with what you have now.[en]|Empieza con lo que tienes ahora.[es]|Commencez par ce que vous avez maintenant.[fr]|Beginnen Sie mit dem, was Sie jetzt haben.[de]|Inizia con ciò che hai ora.[it]|今持っているものから始めてください。[ja]|Comece com o que você tem agora.[pt]|Начните с того, что у вас есть сейчас.[ru]|从你现在拥有的开始。[zh]"
)
wealth_starting_wealth = Verbiage(
    "Starting wealth[en]|Patrimonio inicial[es]|Richesse de départ[fr]|Anfangsvermögen[de]|Patrimonio iniziale[it]|初期資産[ja]|Patrimônio inicial[pt]|Начальное состояние[ru]|初始财富[zh]"
)
wealth_starting_wealth_help = Verbiage(
    "You can type 1M for one million, or 250k for 250,000.[en]|Puedes escribir 1M para un millón, o 250k para 250.000.[es]|Vous pouvez taper 1M pour un million, ou 250k pour 250,000.[fr]|Sie können 1M für eine Million eingeben, oder 250k für 250.000.[de]|Puoi digitare 1M per un milione, o 250k per 250,000.[it]|1Mと入力すると100万、250kと入力すると25万になります。[ja]|Você pode digitar 1M para um milhão, ou 250k para 250,000.[pt]|Можно ввести 1M для миллиона или 250k для 250 000.[ru]|你可以输入1M表示一百万，或者250k表示250,000。[zh]"
)
wealth_cash_buffer = Verbiage(
    "Cash you keep aside[en]|Efectivo que mantienes aparte[es]|Liquide que vous gardez de côté[fr]|Bargeld, das Sie beiseitelegen[de]|Liquido che tieni da parte[it]|別に取っておく現金[ja]|Dinheiro que você mantém de lado[pt]|Наличные, которые вы оставляете в стороне[ru]|你另外留出的现金[zh]"
)
wealth_cash_buffer_help = Verbiage(
    "A reserve that is not part of the invested mix.[en]|Una reserva que no forma parte de la mezcla invertida.[es]|Une réserve qui ne fait pas partie du mélange investi.[fr]|Eine Reserve, die nicht zum investierten Mix gehört.[de]|Una riserva che non fa parte del mix investito.[it]|投資配分に含まれない備えです。[ja]|Uma reserva que não faz parte da combinação investida.[pt]|Резерв, который не входит в инвестиционный набор.[ru]|一笔不属于投资组合的储备。[zh]"
)

# flows
flows_title = Verbiage(
    "Contributions & Withdrawals[en]|Contribuciones y retiros[es]|Contributions et retraits[fr]|Zahlungen und Abhebungen[de]|Contributi e prelievi[it]|出し入れ[ja]|Contribuições e retiradas[pt]|Вклады и выводы[ru]|存入和取出[zh]"
)
flows_prompt = Verbiage(
    "Yearly amounts. Use 0k if one of them does not apply.[en]|Importes anuales. Usa 0k si alguno no aplica.[es]|Montants annuels. Utilisez 0k si l'un d'eux ne s'applique pas.[fr]|Jährliche Beträge. Verwenden Sie 0k, wenn einer davon nicht zutrifft.[de]|Importi annuali. Usa 0k se uno di essi non si applica.[it]|年ごとの金額です。当てはまらないものは0kにしてください。[ja]|Quantias anuais. Use 0k se um deles não se aplicar.[pt]|Годовые суммы. Укажите 0k, если что-то из этого не применяется.[ru]|每年的金额。如果其中一项不适用，请填0k。[zh]"
)
flows_contributions = Verbiage(
    "Added each year[en]|Añadido cada año[es]|Ajouté chaque année[fr]|Jährlich hinzugefügt[de]|Aggiunto ogni anno[it]|毎年追加[ja]|Adicionado anualmente[pt]|Вносится каждый год[ru]|每年存入[zh]"
)
flows_contributions_help = Verbiage(
    "New savings put in every year.[en]|Ahorro nuevo que se aporta cada año.[es]|Nouvelle épargne versée chaque année.[fr]|Neue Ersparnisse, die jedes Jahr eingezahlt werden.[de]|Nuovi risparmi versati ogni anno.[it]|毎年入れる新しい貯蓄です。[ja]|Novas poupanças colocadas a cada ano.[pt]|Новые сбережения, которые вносятся каждый год.[ru]|每年投入的新储蓄。[zh]"
)
flows_withdrawals = Verbiage(
    "Taken out each year[en]|Retirado cada año[es]|Retiré chaque année[fr]|Jährlich abgezogen[de]|Prelevato ogni anno[it]|毎年取り出す[ja]|Retirado anualmente[pt]|Снимается каждый год[ru]|每年取出[zh]"
)
flows_withdrawals_help = Verbiage(
    "Spending paid from the portfolio every year.[en]|Gasto pagado con la cartera cada año.[es]|Dépenses payées du portefeuille chaque année.[fr]|Ausgaben aus dem Portfolio jährlich bezahlt[de]|Spese pagate dal portafoglio ogni anno[it]|毎年ポートフォリオから支払う支出です。[ja]|Despesas pagas do portfólio anualmente[pt]|Расходы, которые каждый год оплачиваются из портфеля.[ru]|每年从投资组合中支付的开支。[zh]"
)

# mix
mix_title = Verbiage(
    "How your money is invested[en]|Cómo está invertido tu dinero[es]|Comment votre argent est investi[fr]|Wie Ihr Geld investiert wird[de]|Come è investito il tuo denaro[it]|あなたのお金がどのように投資されているか[ja]|Como seu dinheiro é investido[pt]|Как вложены ваши деньги[ru]|你的钱是如何投资的[zh]"
)
mix_prompt = Verbiage(
    "Percentages of the invested mix. They should add up to 100%.[en]|Porcentajes de la mezcla invertida. Deben sumar el 100%.[es]|Pourcentages du mélange investi. Ils doivent totaliser 100%.[fr]|Prozentanteile des investierten Mix. Sie sollten insgesamt 100% ergeben.[de]|Percentuali del mix investito. Devono totalizzare 100%.[it]|投資配分の割合です。合計が100%になるようにしてください。[ja]|Percentuais da combinação investida. Devem somar 100%.[pt]|Доли инвестиционного набора в процентах. В сумме они должны давать 100%.[ru]|投资组合的百分比。它们应合计为100%。[zh]"
)
mix_money_market = Verbiage(
    "Money market %[en]|Mercado monetario %[es]|Marché monétaire %[fr]|Geldmarkt %[de]|Mercato monetario %[it]|マネーマーケット %[ja]|Mercado monetário %[pt]|Денежный рынок %[ru]|货币市场 %[zh]"
)
mix_bonds = Verbiage(
    "Bonds %[en]|Bonos %[es]|Obligations %[fr]|Anleihen %[de]|Obbligazioni %[it]|債券 %[ja]|Obrigações %[pt]|Облигации %[ru]|债券 %[zh]"
)
mix_stocks = Verbiage(
    "Stocks %[en]|Acciones %[es]|Actions %[fr]|Aktien %[de]|Azioni %[it]|株式 %[ja]|Ações %[pt]|Акции %[ru]|股票 %[zh]"
)
markets_title = Verbiage(
    "How markets may behave[en]|Cómo pueden comportarse los mercados[es]|Comment les marchés peuvent se comporter[fr]|Wie die Märkte sich verhalten können[de]|Come possono comportarsi i mercati[it]|市場がどう動くか[ja]|Como os mercados podem se comportar[pt]|Как могут вести себя рынки[ru]|市场可能如何表现[zh]"
)
markets_prompt = Verbiage(
    "Typical yearly growth, and how bumpy the ride is. Not a forecast.[en]|Crecimiento anual típico y cuánto oscila. No es un pronóstico.[es]|Croissance annuelle typique, et à quel point le parcours est irrégulier. Ce n'est pas une prévision.[fr]|Typisches jährliches Wachstum und wie unruhig der Verlauf ist. Keine Prognose.[de]|Crescita annuale tipica e quanto è accidentato il percorso. Non è una previsione.[it]|典型的な年間の伸びと、どれくらい起伏があるかです。予測ではありません。[ja]|Crescimento anual típico e o quanto o percurso é irregular. Não é uma previsão.[pt]|Типичный годовой рост и насколько неровным будет путь. Это не прогноз.[ru]|典型的年增长，以及过程有多颠簸。这不是预测。[zh]"
)
markets_money_market = Verbiage(
    "Money market growth %[en]|Crecimiento del mercado monetario %[es]|Croissance du marché monétaire %[fr]|Wachstum des Geldmarkts %[de]|Crescita del mercato monetario %[it]|マネーマーケットの成長 %[ja]|Crescimento do mercado monetário %[pt]|Рост денежного рынка %[ru]|货币市场增长 %[zh]"
)
markets_money_market_bumpiness = Verbiage(
    "Money market bumpiness %[en]|Oscilación del mercado monetario %[es]|Irrégularité du marché monétaire %[fr]|Unruhe des Geldmarkts %[de]|Irregolarità del mercato monetario %[it]|マネーマーケットの起伏 %[ja]|Irregularidade do mercado monetário %[pt]|Неровность денежного рынка %[ru]|货币市场颠簸 %[zh]"
)
markets_bonds = Verbiage(
    "Bonds growth %[en]|Crecimiento de los bonos %[es]|Croissance des obligations %[fr]|Wachstum der Anleihen %[de]|Crescita delle obbligazioni %[it]|債券の成長 %[ja]|Crescimento das obrigações %[pt]|Рост облигаций %[ru]|债券增长 %[zh]"
)
markets_bonds_bumpiness = Verbiage(
    "Bonds bumpiness %[en]|Oscilación de los bonos %[es]|Irrégularité des obligations %[fr]|Unruhe der Anleihen %[de]|Irregolarità delle obbligazioni %[it]|債券の起伏 %[ja]|Irregularidade das obrigações %[pt]|Неровность облигаций %[ru]|债券颠簸 %[zh]"
)
markets_stocks = Verbiage(
    "Stocks growth %[en]|Crecimiento de las acciones %[es]|Croissance des actions %[fr]|Wachstum der Aktien %[de]|Crescita delle azioni %[it]|株式の成長 %[ja]|Crescimento das ações %[pt]|Рост акций %[ru]|股票增长 %[zh]"
)
markets_stocks_bumpiness = Verbiage(
    "Stocks bumpiness %[en]|Oscilación de las acciones %[es]|Irrégularité des actions %[fr]|Unruhe der Aktien %[de]|Irregolarità delle azioni %[it]|株式の起伏 %[ja]|Irregularidade das ações %[pt]|Неровность акций %[ru]|股票颠簸 %[zh]"
)

run_title = Verbiage(
    "Run the projection[en]|Ejecutar la proyección[es]|Exécuter la projection[fr]|Die Projektion ausführen[de]|Eseguire la proiezione[it]|試算を実行[ja]|Executar a projeção[pt]|Запустить проекцию[ru]|运行预测[zh]"
)
run_prompt = Verbiage(
    "How far ahead, and how many possible futures.[en]|Hasta dónde mirar y cuántos futuros posibles.[es]|Jusqu'où regarder, et combien de futurs possibles.[fr]|Wie weit voraus, und wie viele mögliche Zukünfte.[de]|Quanto avanti, e quanti futuri possibili.[it]|どれだけ先まで見るか、そして可能な未来はいくつか。[ja]|Até onde olhar, e quantos futuros possíveis.[pt]|Насколько далеко вперёд и сколько возможных вариантов будущего.[ru]|向前看多远，以及有多少种可能的未来。[zh]"
)
run_horizon = Verbiage(
    "Years to look ahead[en]|Años por delante[es]|Années à regarder en avant[fr]|Jahre vorausblicken[de]|Anni da guardare avanti[it]|先を見る年数[ja]|Anos para olhar à frente[pt]|На сколько лет смотреть вперёд[ru]|向前看的年数[zh]"
)
run_nb_projections = Verbiage(
    "Number of futures[en]|Número de futuros[es]|Nombre de futurs[fr]|Anzahl der Zukünfte[de]|Numero di futuri[it]|可能な未来の数[ja]|Número de futuros[pt]|Число вариантов будущего[ru]|可能的未来数[zh]"
)
run_rng_seed = Verbiage(
    "Random seed[en]|Semilla aleatoria[es]|Graine aléatoire[fr]|Zufälliger Startwert[de]|Seme casuale[it]|ランダムシード[ja]|Semente aleatória[pt]|Случайное зерно[ru]|随机种子[zh]"
)
review_title = Verbiage(
    "Review[en]|Revisión[es]|Révision[fr]|Überprüfung[de]|Revisione[it]|確認[ja]|Revisão[pt]|Обзор[ru]|回顾[zh]"
)
review_prompt = Verbiage(
    "Here is what the tour collected. The projection engine is not called yet.[en]|Esto es lo que ha recogido el recorrido. El motor de proyección aún no se ha llamado.[es]|Voici ce que le parcours a recueilli. Le moteur de projection n'est pas encore appelé.[fr]|Hier ist, was der Rundgang gesammelt hat. Die Projektionsengine wird noch nicht aufgerufen.[de]|Ecco che cosa ha raccolto il percorso. Il motore di proiezione non è ancora chiamato.[it]|ここまでの質問で集めた内容です。試算エンジンはまだ呼び出していません。[ja]|Aqui está o que o percurso recolheu. O motor de projeção ainda não foi chamado.[pt]|Вот что собрал этот обход. Движок проекции ещё не вызывается.[ru]|以下是本次引导收集的内容。预测引擎尚未调用。[zh]"
)


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
