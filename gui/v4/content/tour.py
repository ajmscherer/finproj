# finproj - v4 section graph (copy and edges, not engine rules)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from model.conditions import goal_is_other
from model.definition import TourDefinition
from model.step import FieldSpec, Step

from gui.v4.content.verbiage import Verbiage

# goal
goal_title = Verbiage("Goal[en]|Objectif[fr]|Ziel[de]|Obiettivo[it]|目標[ja]|Objetivo[pt]|目標[ru]|目标[zh]")
goal_prompt = Verbiage("How would you like to use this app?[en]|Comment aimeriez-vous utiliser cette application?[fr]|Wie möchten Sie diese Anwendung nutzen?[de]|Come vorresti utilizzare questa applicazione?[it]|このアプリをどのように使用しますか?[ja]|Como você gostaria de usar este aplicativo?[pt]|Как вы хотели бы использовать это приложение?[ru]|你希望如何使用这个应用程序?[zh]")

goal_prompt = Verbiage("How would you like to use this app?[en]|Comment aimeriez-vous utiliser cette application?[fr]|Wie möchten Sie diese Anwendung nutzen?[de]|Come vorresti utilizzare questa applicazione?[it]|このアプリをどのように使用しますか?[ja]|Como você gostaria de usar este aplicativo?[pt]|Как вы хотели бы использовать это приложение?[ru]|你希望如何使用这个应用程序?[zh]")
goal_kind_title = Verbiage("What should this projection help you decide?[en]|Qu'est-ce que cette projection devrait vous aider à décider?[fr]|Was soll diese Projektion Ihnen helfen?[de]|Cosa dovrebbe aiutarti a decidere questa proiezione?[it]|この投影はあなたにどのような助けをしますか?[ja]|O que esta projeção deve ajudar você a decidir?[pt]|Что должна помочь вам решить эта проекция?[ru]|这个投影应该帮助你决定什么?[zh]")
goal_kind_retire_when = Verbiage("Decide when I can retire[en]|Décidez quand je peux prendre ma retraite[fr]|Entscheiden Sie, wann ich abziehen kann[de]|Decide quando posso andare in pensione[it]|このアプリをどのように使用しますか?[ja]|Como você gostaria de usar este aplicativo?[pt]|Как вы хотели бы использовать это приложение?[ru]|你希望如何使用这个应用程序?[zh]")
goal_kind_save_for_income = Verbiage("Decide how much I need to save [en]|Décidez combien je dois économiser[fr]|Entscheiden Sie, wie viel ich sparen muss[de]|Decide quanto devo salvare[it]|このアプリをどのように使用しますか?[ja]|Como você gostaria de usar este aplicativo?[pt]|Как вы хотели бы использовать это приложение?[ru]|你希望如何使用这个应用程序?[zh]")
goal_kind_other = Verbiage("Other usage[en]|Autre utilisation[fr]|Andere Verwendung[de]|Altro utilizzo[it]|このアプリをどのように使用しますか?[ja]|Como você gostaria de usar este aplicativo?[pt]|Как вы хотели бы использовать это приложение?[ru]|你希望如何使用这个应用程序?[zh]")
goal_kind_other_help = Verbiage("Pick the usage that best describes what you want to do.[en]|Choisissez l'utilisation qui décrit le mieux ce que vous voulez faire.[fr]|Wählen Sie die Verwendung, die am besten beschreibt, was Sie tun möchten.[de]|Scegli l'utilizzo che descrive meglio ciò che vuoi fare.[it]|このアプリをどのように使用しますか?[ja]|Escolha o uso que melhor descreve o que você quer fazer.[pt]|Выберите использование, которое лучше всего описывает, что вы хотите сделать.[ru]|选择最能描述你想要做什么的使用。[zh]")

# wealth
wealth_title = Verbiage("Your Wealth[en]|Votre richesse[fr]|Ihr Vermögen[de]|Il tuo patrimonio[it]|あなたの財産[ja]|Seu patrimônio[pt]|你的财富[ru]|你的财富[zh]")
wealth_prompt = Verbiage("Start with what you have now.[en]|Commencez par ce que vous avez maintenant.[fr]|Beginnen Sie mit dem, was Sie jetzt haben.[de]|Inizia con ciò che hai ora.[it]|今持っているものから始めます。[ja]|Come comece com o que você tem agora.[pt]|Начните с того, что у вас есть сейчас.[ru]|Начните с того, что у вас есть сейчас.[zh]")
wealth_starting_wealth = Verbiage("Starting wealth[en]|Richesse de départ[fr]|Anfangsvermögen[de]|Patrimonio iniziale[it]|最初の財産[ja]|Patrimônio inicial[pt]|初始财富[ru]|初始财富[zh]")
wealth_starting_wealth_help = Verbiage("You can type 1M for one million, or 250k for 250,000.[en]|Vous pouvez taper 1M pour un million, ou 250k pour 250,000.[fr]|Sie können 1M für eine Million, oder 250k für 250,000.[de]|Puoi digitare 1M per un milione, o 250k per 250,000.[it]|1Mは100万、250kは25万を意味します。[ja]|Você pode digitar 1M para um milhão, ou 250k para 250,000.[pt]|你可以输入1M表示一百万，或者250k表示250,000。[ru]|你可以输入1M表示一百万，或者250k表示250,000。[zh]")
wealth_cash_buffer = Verbiage("Cash you keep aside[en]|Liquide que vous gardez de côté[fr]|Zahlungseinstellung[de]|Liquido che tieni da parte[it]|現金を残しておく[ja]|Dinheiro que você mantém de lado[pt]|你保留的现金[ru]|你保留的现金[zh]")
wealth_cash_buffer_help = Verbiage("A reserve that is not part of the invested mix.[en]|Un réservoir qui n'est pas partie du mix investi.[fr]|Ein Reservoir, das nicht Teil des investierten Mix ist.[de]|Un deposito che non è parte del mix investito.[it]|投資されたミックスに含まれないリザーブ。[ja]|Um depósito que não é parte do mix investido.[pt]|投资混合中不包含的储备。[ru]|投资混合中不包含的储备。[zh]")

# flows
flows_title = Verbiage("Money you add or take out[en]|Vous ajoutez ou retirez de l'argent[fr]|Sie addieren oder subtrahieren Geld[de]|Aggiungi o togli denaro[it]|あなたが追加または取り出すお金[ja]|Você adiciona ou retira dinheiro[pt]|你添加或提取的钱[ru]|你添加或提取的钱[zh]")
flows_prompt = Verbiage("Yearly amounts. Use 0k if one of them does not apply.[en]|Montants annuels. Utilisez 0k si l'un d'eux ne s'applique pas.[fr]|Jährliche Beträge. Verwenden Sie 0k, wenn eine von ihnen nicht zutrifft.[de]|Importi annuali. Usa 0k se uno di essi non si applica.[it]|毎年の金額。どれかが適用されない場合は0kを使用します。[ja]|Quantias anuais. Use 0k se um deles não se aplicar.[pt]|每年金额。如果其中一个不适用，请使用0k。[ru]|每年金额。如果其中一个不适用，请使用0k。[zh]")
flows_contributions = Verbiage("Added each year[en]|Ajouté chaque année[fr]|Jährlich hinzugefügt[de]|Aggiunto ogni anno[it]|毎年追加[ja]|Adicionado anualmente[pt]|每年添加[ru]|每年添加[zh]")
flows_contributions_help = Verbiage("New savings put in every year.[en]|Nouveaux économies mis chaque année.[fr]|Neue Ersparnisse jährlich hinzugefügt[de]|Nuove risparmi aggiunti ogni anno[it]|新しい節約を毎年投入します。[ja]|Novas economias adicionadas anualmente[pt]|每年添加新的储蓄。[ru]|每年添加新的储蓄。[zh]")
flows_withdrawals = Verbiage("Taken out each year[en]|Retiré chaque année[fr]|Jährlich abgezogen[de]|Rimosso ogni anno[it]|毎年取出[ja]|Retirado anualmente[pt]|每年取出[ru]|每年取出[zh]")
flows_withdrawals_help = Verbiage("Spending paid from the portfolio every year.[en]|Dépenses payées du portefeuille chaque année.[fr]|Ausgaben aus dem Portfolio jährlich bezahlt[de]|Spese pagate dal portafoglio ogni anno[it]|ポートフォリオから毎年支払う支出。[ja]|Despesas pagas do portfólio anualmente[pt]|从投资组合中每年支付支出。[ru]|从投资组合中每年支付支出。[zh]")

# mix
mix_title = Verbiage("How your money is invested[en]|Comment votre argent est investi[fr]|Wie Ihr Geld investiert wird[de]|Come è investito il tuo denaro[it]|あなたのお金がどのように投資されているか[ja]|Como seu dinheiro é investido[pt]|你的钱是如何投资的[ru]|你的钱是如何投资的[zh]")
mix_prompt = Verbiage("Percentages of the invested mix. They should add up to 100%.[en]|Pourcentages de la mix investie. Ils doivent totaliser 100%.[fr]|Prozentanteile des investierten Mix. Sie sollten insgesamt 100% ergeben.[de]|Percentuali del mix investito. Devono totalizzare 100%.[it]|投資されたミックスのパーセンテージ。合計で100%になる必要があります。[ja]|Percentuais do mix investido. Devem totalizar 100%.[pt]|投资混合的百分比。它们应该加起来是100%。[ru]|投资混合的百分比。它们应该加起来是100%。[zh]")
mix_money_market = Verbiage("Money market %[en]|Pourcentage du money market[fr]|Prozent des Money Market[de]|Percentuale del money market[it]|マネーマーケットのパーセンテージ[ja]|Percentual do money market[pt]|钱市场的百分比[ru]|钱市场的百分比[zh]")
mix_bonds = Verbiage("Bonds %[en]|Pourcentage des obligations[fr]|Prozent der Obligationen[de]|Percentuale delle obbligazioni[it]|債券のパーセンテージ[ja]|Percentual das obbligazioni[pt]|债券的百分比[ru]|债券的百分比[zh]")
mix_stocks = Verbiage("Stocks %[en]|Pourcentage des actions[fr]|Prozent der Aktien[de]|Percentuale delle azioni[it]|株式のパーセンテージ[ja]|Percentual das ações[pt]|股票的百分比[ru]|股票的百分比[zh]")
markets_title = Verbiage("How markets may behave[en]|Comment les marchés peuvent se comporter[fr]|Wie die Märkte sich verhalten können[de]|Come si comportano i mercati[it]|市場がどのように振る舞うか[ja]|Como os mercados podem se comportar[pt]|市场可能如何表现[ru]|市场可能如何表现[zh]")
markets_prompt = Verbiage("Typical yearly growth, and how bumpy the ride is. Not a forecast.[en]|Croissance typique annuelle, et à quel point le voyage peut être accidenté. Pas un prévision.[fr]|Typische jährliche Wachstumsrate und wie bumpy der Fahrt sein kann. Keine Prognose.[de]|Crescita tipica annuale e quanto accidentata può essere la corsa. Non una previsione.[it]|典型的な年間成長率と、どれだけ荒れた乗り物か。予測ではありません。[ja]|Taxa de crescimento anual típica e quanto bumpy pode ser o trajeto. Não é uma previsão.[pt]|典型的な年間成長率と、どれだけ荒れた乗り物か。予測ではありません。[ru]|典型的年增长率和旅程的颠簸程度。不是预测。[zh]")
markets_money_market = Verbiage("Money market growth %[en]|Croissance du money market[fr]|Wachstumsrate des Money Market[de]|Crescita del money market[it]|マネーマーケットの成長率[ja]|Taxa de crescimento do money market[pt]|钱市场的增长率[ru]|钱市场的增长率[zh]")
markets_money_market_bumpiness = Verbiage("Money market bumpiness %[en]|Bumpiness du money market[fr]|Bumpiness des Money Market[de]|Bumpiness del money market[it]|マネーマーケットの荒れ具合[ja]|Bumpiness do money market[pt]|钱市场的荒れ具合[ru]|钱市场的荒れ具合[zh]")
markets_bonds = Verbiage("Bonds growth %[en]|Croissance des obligations[fr]|Wachstumsrate der Obligationen[de]|Crescita delle obbligazioni[it]|債券の成長率[ja]|Taxa de crescimento das obbligazioni[pt]|债券的成長率[ru]|债券的成長率[zh]")
markets_bonds_bumpiness = Verbiage("Bonds bumpiness %[en]|Bumpiness des obligations[fr]|Bumpiness der Obligationen[de]|Bumpiness delle obbligazioni[it]|債券の荒れ具合[ja]|Bumpiness das obbligazioni[pt]|债券的荒れ具合[ru]|债券的荒れ具合[zh]")
markets_stocks = Verbiage("Stocks growth %[en]|Croissance des actions[fr]|Wachstumsrate der Aktien[de]|Crescita delle azioni[it]|株式の成長率[ja]|Taxa de crescimento das ações[pt]|股票的成長率[ru]|股票的成長率[zh]")
markets_stocks_bumpiness = Verbiage("Stocks bumpiness %[en]|Bumpiness des actions[fr]|Bumpiness der Aktien[de]|Bumpiness delle azioni[it]|株式の荒れ具合[ja]|Bumpiness das ações[pt]|股票的荒れ具合[ru]|股票的荒れ具合[zh]")

run_title = Verbiage("Run the projection[en]|Exécuter la projection[fr]|Die Projektion ausführen[de]|Eseguire la proiezione[it]|投影を実行[ja]|Executar a projeção[pt]|运行投影[ru]|运行投影[zh]")
run_prompt = Verbiage("How far ahead, and how many possible futures.[en]|À quelle distance, et combien de futures possibles.[fr]|Wie weit in die Zukunft, und wie viele mögliche Zukunftsfutures.[de]|Quanto avanti, e quante possibili future.[it]|どれだけ先まで見るか、そして可能な未来はいくつか。[ja]|Quanto adiante, e quantas possíveis futuras.[pt]|多久以后，以及可能有多少未来。[ru]|多久以后，以及可能有多少未来。[zh]")
run_horizon = Verbiage("Years to look ahead[en]|Années à regarder[fr]|Jahre zu betrachten[de]|Anni da guardare[it]|先を見る年数[ja]|Anos para olhar[pt]|查看年数[ru]|查看年数[zh]")
run_nb_projections = Verbiage("Number of futures[en]|Nombre de futures[fr]|Anzahl der Zukunftsfutures[de]|Numero di future[it]|可能な未来の数[ja]|Número de futuras[pt]|可能的未来数[ru]|可能的未来数[zh]")
run_rng_seed = Verbiage("Random seed[en]|Seed aléatoire[fr]|Zufälliger Seed[de]|Seed casuale[it]|ランダムシード[ja]|Seed aleatório[pt]|随机种子[ru]|随机种子[zh]")
review_title = Verbiage("Review[en]|Révision[fr]|Überprüfung[de]|Revisione[it]|レビュー[ja]|Revisão[pt]|审查[ru]|审查[zh]")
review_prompt = Verbiage("Here is what the tour collected. The projection engine is not called yet.[en]|Voici ce que la visite a collecté. L'appel de l'appareil de projection n'est pas encore effectué.[fr]|Hier ist, was die Tour gesammelt hat. Die Projektionseinheit wird noch nicht aufgerufen.[de]|Ecco cosa la visita ha raccolto. L'unità di proiezione non è ancora chiamata.[it]|ここでは、ツアーが収集したものを示します。投影エンジンはまだ呼び出されていません。[ja]|Aqui está o que a visita coletou. O motor de projeção ainda não foi chamado.[pt]|这里是你收集到的内容。投影引擎还没有被调用。[ru]|这里是你收集到的内容。投影引擎还没有被调用。[zh]")


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
                FieldSpec("mix.money_market", mix_money_market, "percent", min=0, max=100),
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
                FieldSpec("markets.bonds.mu", markets_bonds, "percent", min=-20, max=80),
                FieldSpec(
                    "markets.bonds.sigma", markets_bonds_bumpiness, "percent", min=0, max=100
                ),
                FieldSpec("markets.stocks.mu", markets_stocks, "percent", min=-20, max=80),
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
