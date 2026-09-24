# finproj - v4 section graph (copy and edges, not engine rules)
# Copyright (C) 2025-2026 Alex Scherer

from __future__ import annotations

from model.conditions import goal_is_retire_when, goal_is_save_for_income
from model.definition import TourDefinition
from model.step import FieldSpec, Step

from gui.v4.content.verbiage import Verbiage

# goal
goal_title = Verbiage(
    {
        "en":"Goals",
        "es":"Objetivos",
        "fr":"Objectifs",
        "de":"Ziele",
        "it":"Obiettivi",
        "ja":"目標s",
        "pt":"Objetivos",
        "ru":"Цели",
        "zh":"目标s",
    }
)
goal_prompt = Verbiage(
    {
    "en":"This application is designed to help you make decisions regarding your retirement. There are different manners to approach the problem. This step will help determine which approach is best given the questions on your mind",
    "es":"Esta aplicación está diseñada para ayudarte a tomar decisiones relacionadas con tu retiro. Hay diferentes maneras de abordar el problema. Este paso te ayudará a determinar qué enfoque es el mejor dado las preguntas en tu mente",
    "fr":"Cette application est conçue pour vous aider à prendre des décisions concernant votre retraite. Il existe différentes manières d'aborder le problème. Cette étape vous aidera à déterminer quelle approche est la meilleure données les questions sur votre esprit",
    "de":"Diese Anwendung ist konzipiert, um Ihnen dabei zu helfen, Entscheidungen bezüglich Ihrer Rente zu treffen. Es gibt verschiedene Möglichkeiten, das Problem anzugehen. Dieser Schritt wird Ihnen helfen, zu bestimmen, welche Methode am besten geeignet ist, gegeben die Fragen in Ihrem Kopf",
    "it":"Questa applicazione è progettata per aiutarti a prendere decisioni relative alla tua pensione. Ci sono diverse maniere di affrontare il problema. Questo passo ti aiuterà a determinare quale approccio è il migliore dato le domande nella tua mente",
    "ja":"このアプリは、あなたの引退に関する意思決定を支援するように設計されています。問題に対する異なるアプローチがあります。このステップは、あなたの頭にある質問に基づいて、最適なアプローチを決定するのに役立ちます",
    "pt":"Esta aplicação é projetada para ajudar você a tomar decisões relacionadas com sua aposentadoria. Existem diferentes maneiras de abordar o problema. Este passo ajudará a determinar qual abordagem é a melhor dada as perguntas em sua mente",
    "ru":"Это приложение разработано для помощи вам принимать решения относительно вашей пенсии. Существуют различные способы решения проблемы. Этот шаг поможет определить, какой подход является наиболее подходящим, учитывая вопросы в вашем уме",
    "zh":"这个应用程序旨在帮助您做出与退休相关的决策。有不同的方法来解决这个问题。这一步将帮助确定哪种方法最适合您的问题"
    })

goal_kind_title = Verbiage(
    {
    "en":"How can this application help you?",
    "es":"¿Cómo puede esta aplicación ayudarte?",
    "fr":"Comment cette application peut vous aider?",
    "de":"Wie kann diese Anwendung Ihnen helfen?",
    "it":"Come può questa applicazione aiutarti?",
    "ja":"このアプリは、あなたをどのように助けることができますか？",
    "pt":"Como esta aplicação pode ajudar-lhe?",
    "ru":"Как это приложение может помочь вам?",
    "zh":"这个应用程序如何帮助您？" 
    })

goal_kind_help = Verbiage(
    {
    "en":"Choose the question that corresponds to your situation.",
    "es":"Elige la pregunta que corresponda a tu situación.",
    "fr":"Choisissez la question qui correspond à votre situation.",
    "de":"Wählen Sie die Frage, die Ihrer Situation entspricht.",
    "it":"Scegli la domanda che corrisponde alla tua situazione.",
    "ja":"あなたの状況に対応する質問を選んでください。",
    "pt":"Escolha a pergunta que corresponde à sua situação.",
    "ru":"Выберите вопрос, который соответствует вашей ситуации.",
    "zh":"选择与您的情况相对应的问题。"
    })


goal_kind_retire_when = Verbiage(
    {
    "en":"When shall I have accumulated enough wealth to retire?",
    "es":"¿Cuándo acumularás suficiente riqueza para retirarte?",
    "fr":"Quand aurais-je accumulé suffisamment de richesse pour prendre ma retraite?",
    "de":"Wann haben Sie genug Vermögen gesammelt, um in Rente zu gehen?",
    "it":"Quando accumulerete abbastanza ricchezza per andare in pensione?",
    "ja":"いつあなたが十分な富を蓄えて引退できるかを決める",
    "pt":"Quando você terá acumulado suficiente riqueza para se aposentar?",
    "ru":"Когда вы накопите достаточно состояния, чтобы выйти на пенсию?",
    "zh":"你什么时候能积累足够的财富退休？"
    })
goal_kind_save_for_income = Verbiage(
    {
    "en":"I know when I want to retire. How much do I need to save annually?",
    "es":"Sé cuándo quiero retirarme. ¿Cuánto necesito ahorrar anualmente?",
    "fr":"Je sais quand je veux prendre ma retraite. Combien dois-je épargner annuellement?",
    "de":"Ich weiß, wann ich in Rente gehen möchte. Wie viel muss ich jährlich sparen?",
    "it":"So quando vuoi andare in pensione. Quanto devo risparmiare annualmente?",
    "ja":"引退したい時期がわかっています。年間でどれくらいの金額を貯める必要がありますか？",
    "pt":"Sei quando você quer se aposentar. Quanto preciso poupar anualmente?",
    "ru":"Я знаю, когда я хочу выйти на пенсию. Сколько мне нужно накопить ежегодно?",
    "zh":"我知道我什么时候想退休。我每年需要存多少钱？"
    })
goal_kind_other = Verbiage(
    {
    "en":"Other",
    "es":"Otro",
    "fr":"Autre",
    "de":"Andere",
    "it":"Altro",
    "ja":"その他",
    "pt":"Outro",
    "ru":"Другое",
    "zh":"其他"
    })
goal_kind_other_help = Verbiage(
    {
    "en":"Choose what you want to do.",
    "es":"Elige lo que quieres hacer.",
    "fr":"Choisissez ce que vous voulez faire.",
    "de":"Wählen Sie, was Sie tun möchten.",
    "it":"Scegli ciò che vuoi fare.",
    "ja":"何をしたいか選んでください。",
    "pt":"Escolha o que você quer fazer.",
    "ru":"Выберите, что вы хотите сделать.",
    "zh":"选择你想做什么。"
    })
goal_thinking_mode_title = Verbiage(
    {
    "en":"What is your thinking mode for retirement?",
    "es":"¿Qué modo de pensamiento tienes para tu retiro?",
    "fr":"Quel mode de pensée avez-vous pour votre retraite?",
    "de":"Welcher Denkmodus haben Sie für Ihre Rente?",
    "it":"Quale modalità di pensiero hai per la tua pensione?",
    "ja":"あなたの引退に対する思考モードは何ですか？",
    "pt":"Qual o modo de pensamento você tem para sua aposentadoria?",
    "ru":"Какой режим мышления у вас для выхода на пенсию?",
    "zh":"你退休时的思考模式是什么？"
    })
goal_thinking_mode_help = Verbiage(
    {
    "en":"Capital vs. Income: Choose the mode you want to use to think about your retirement.",
    "es":"Capital vs. Ingreso: Elige el modo de pensamiento que quieres usar para pensar sobre tu retiro.",
    "fr":"Capital vs. Revenu: Choisissez le mode de pensée que vous voulez utiliser pour penser à votre retraite.",
    "de":"Kapital vs. Einkommen: Wählen Sie den Denkmodus, den Sie für Ihre Rente verwenden möchten.",
    "it":"Capital vs. Reddito: Scegli la modalità di pensiero che vuoi usare per pensare alla tua pensione.",
    "ja":"資本 vs. 収入: あなたの引退に対する思考モードを選んでください。",
    "pt":"Capital vs. Rendimento: Escolha o modo de pensamento que você quer usar para pensar sobre sua aposentadoria.",
    "ru":"Капитал vs. Доход: Выберите режим мышления, который вы хотите использовать для выхода на пенсию.",
    "zh":"资本 vs. 收入: 选择你退休时的思考模式。"
    })

goal_thinking_mode_capital = Verbiage(
    {
    "en":"I'm interested in priority by the amount of wealth I can achieve when I retire",
    "es":"Estoy interesado en priorizar la cantidad de riqueza que puedo lograr cuando mejubile",
    "fr":"Je suis intéressé par la priorité de la quantité de richesse que je peux atteindre lorsque je prends ma retraite",
    "de":"Ich bin interessiert an der Priorität der Menge an Vermögen, die ich erreichen kann, wenn ich in Rente gehe",
    "it":"Sono interessato alla priorità della quantità di ricchezza che posso raggiungere quando mi pensiono",
    "ja":"私は引退したときに達成できる富の量を優先することに興味があります",
    "pt":"Estou interessado na prioridade da quantidade de riqueza que posso alcançar quando me aposento",
    "ru":"Я интересуюсь приоритетом количества состояния, которое я могу достичь, когда я выхожу на пенсию",
    "zh":"我对退休时能达到的财富量感兴趣"
    })
goal_thinking_mode_income = Verbiage(
    {
    "en":"My focus is more on the amount of annual income I can extract from my wealth when I'm retired",
    "es":"Mi enfoque es más en la cantidad de ingreso anual que puedo extraer de mi riqueza cuando mejubile",
    "fr":"Mon focus est plus sur la quantité de revenu annuel que je peux extraire de ma richesse lorsque je suis en retraite",
    "de":"Mein Fokus ist mehr auf der Menge an jährlichem Einkommen, die ich aus meinem Vermögen extrahieren kann, wenn ich in Rente gehe",
    "it":"Il mio focus è più sulla quantità di reddito annuo che posso estrarre dai miei beni quando mi pensiono",
    "ja":"私の焦点は、私が引退したときに私の富から抽出できる年収の量にあります",
    "pt":"Meu foco é mais na quantidade de rendimento anual que posso extrair de minha riqueza quando me aposento",
    "ru":"Мой фокус больше на количестве ежегодного дохода, которое я могу извлечь из моего состояния, когда я выхожу на пенсию",
    "zh":"我对退休时能从我的财富中提取的年收入量更感兴趣"
    })
goal_target_income = Verbiage(
    {
    "en":"What annual amount do you target for your retirement?",
    "es":"¿Qué monto anual objetivo tienes para tu retiro?",
    "fr":"Quel montant annuel ciblez vous pour votre retraite?",
    "de":"Welches jährliche Ziel haben Sie für Ihre Rente?",
    "it":"Quale importo annuo obiettivo hai per la tua pensione?",
    "ja":"引退後に得たい必要な年収はどれくらいですか？",
    "pt":"Qual montante anual você precisa para sua aposentadoria?",
    "ru":"Какой ежегодный доход цели вы хотели бы, чтобы ваше состояние генерировало с моментая выхода на пенсию?",
    "zh":"你退休后需要多少年收入？"
    })

goal_target_income_help = Verbiage(
    {
    "en":"This is the annual amount you will draw from your own assets (your wealth), from the time you retire. Do not include here the amounts you expect to receive from other sources. For example, if you are eligible to social security retirement, do not include corresponding amount in this target. You can type 50k for 50,000.",
    "es":"Este es el monto anual que vas a retirar de tus propios activos (tu riqueza), desde el momento en que te jubiles. No incluyas aquí los montos que esperas recibir de otras fuentes. Por ejemplo, si eres elegible para la jubilación de la seguridad social, no incluyas el monto correspondiente en este objetivo. Puedes escribir 50k para 50,000.",
    "fr":"C'est le montant annuel que vous retirerez de vos propres actifs (votre richesse), à partir du moment où vous prenez votre retraite. Ne pas inclure ici les montants que vous espérez recevoir d'autres sources. Par exemple, si vous êtes éligible à la retraite de la sécurité sociale, ne pas inclure le montant correspondant dans cette cible. Vous pouvez taper 50k pour 50,000.",
    "de":"Dies ist der jährliche Betrag, den Sie aus Ihren eigenen Vermögenswerten (Ihrem Vermögen) abziehen, ab dem Zeitpunkt, wenn Sie in Rente gehen. Schließen Sie hier nicht die Beträge ein, die Sie von anderen Quellen erwarten. Zum Beispiel, wenn Sie rentenversichert sind, schließen Sie nicht den entsprechenden Betrag in dieses Ziel ein. Sie können 50k für 50,000 eingeben.",
    "it":"Questo è l'importo annuo che si preleva dai propri beni (il tuo patrimonio), dal momento in cui si pensiona. Non includere qui i montanti che aspetti di ricevere da altre fonti. Per esempio, se sei elegibile per la pensione della sicurezza sociale, non includere il corrispondente importo in questo obiettivo. Puoi digitare 50k per 50,000.",
    "ja":"引退後に必要な年収はどれくらいですか？引退後に受け取る予定の他の収入を引いてください。例えば、社会保険の引退が可能な場合は、この目標に対応する金額を含めないでください。50kと入力すると50,000円になります。",
    "pt":"Qual montante anual você precisa para sua aposentadoria? Não inclua aqui os montantes que você espera receber de outras fontes. Por exemplo, se você é elegível para a aposentadoria da segurança social, não inclua o montante correspondente nesta meta. Você pode digitar 50k para 50,000.",
    "ru":"Какой ежегодный доход вам нужен для выхода на пенсию? Не включайте здесь суммы, которые вы ожидаете получить от других источников. Например, если вы имеете право на социальное обеспечение, не включайте соответствующую сумму в эту цель. Можно ввести 50k для 50,000.",
    "zh":"你退休后需要多少年收入？不要包括你预计从其他来源获得的收入。例如，如果你有资格享受社会养老保险，不要将相应的金额包含在这个目标中。你可以输入50k表示50,000元。"
    })

goal_years_to_retire = Verbiage(
    {
    "en":"How many years until you retire?",
    "es":"¿Cuántos años hasta que te jubiles?",
    "fr":"Combien d'années jusqu'à ce que vous preniez votre retraite?",
    "de":"Wie viele Jahre bis Sie in Rente gehen?",
    "it":"Quanti anni fino a che ti pensioni?",
    "ja":"何年後に引退しますか？",
    "pt":"Quantos anos até você se aposentar?",
    "ru":"Сколько лет до выхода на пенсию?",
    "zh":"你还有多少年退休？"
    })
goal_years_to_retire_help = Verbiage(
    {
    "en":"Count the number of years between now and the time you target to retire.",
    "es":"Cuenta el número de años entre ahora y el momento en que quieres jubilarte.",
    "fr":"Comptez le nombre d'années entre maintenant et le moment où vous souhaitez prendre votre retraite.",
    "de":"Zählen Sie die Anzahl der Jahre zwischen jetzt und dem Zeitpunkt, wenn Sie in Rente gehen.",
    "it":"Conta il numero di anni tra ora e il momento in cui vuoi pensionarti.",
    "ja":"今から引退までの年数を数えてください。",
    "pt":"Conte o número de anos entre agora e o momento em que você quer se aposentar.",
    "ru":"Подсчитайте количество лет между сейчас и моментом выхода на пенсию, когда вы хотите выйти на пенсию.",
    "zh":"从现在到你目标退休还有多少年。"
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
    "en":"To do calculations, the model needs to know your current wealth. This includes all assets you own,",
    "es":"Para hacer cálculos, el modelo necesita saber tu riqueza actual. Esto incluye todos los activos que tienes,",
    "fr":"Pour faire des calculs, le modèle a besoin de connaître votre richesse actuelle. Cela inclut tous les actifs que vous possédez,",
    "de":"Um Rechenmodell benötigt Ihre aktuelle Vermögenswerte, um Berechnungen durchzuführen. Dies umfasst alle Vermögenswerte, die Sie besitzen,",
    "it":"Per fare calcoli, il modello ha bisogno di conoscere la tua ricchezza attuale. Questo include tutti i beni che possiedi,",
    "ja":"計算を行うために、モデルはあなたの現在の富を知る必要があります。これにはあなたが所有するすべての資産が含まれます。",
    "pt":"Para fazer cálculos, o modelo precisa saber sua riqueza atual. Isso inclui todos os ativos que você possui,",
    "ru":"Для выполнения расчетов модель должна знать ваше текущее состояние. Это включает все активы, которыми вы владеете,",
    "zh":"为了进行计算，模型需要知道你的当前财富。这包括你拥有的所有资产。"
    })
wealth_starting_wealth = Verbiage(
    {
    "en":"Your amount of wealth as of today",
    "es":"Tu cantidad de riqueza hoy",
    "fr":"Votre montant de richesse aujourd'hui",
    "de":"Ihr Vermögen heute",
    "it":"La tua ricchezza odierna",
    "ja":"今日のあなたの富の金額",
    "pt":"Sua quantidade de riqueza hoje",
    "ru":"Ваше состояние сегодня",
    "zh":"你今天的财富金额"
    })
wealth_starting_wealth_help = Verbiage(
    {
    "en":"Provide here the total amount of your wealth as of today. Include real estate, stocks, bonds, cash, and other assets. Do not reduce this amount by the debt you owe. The model assumes that the servicing of the debt is covered by your existing income and, after you retire, in the amount you can draw from your wealth. Specific situations will be addressed later, for example in case there is a very substantial amount of capital outstanding that is can't be paid back in your lifetime.",
    "es":"Proporciona aquí el monto total de tu riqueza hoy. Incluye bienes raíces, acciones, bonos, efectivo y otros activos. No reduzcas este monto por la deuda que debes. El modelo asume que el servicio de la deuda está cubierto por tu ingreso actual y, después de tu retiro, en la cantidad que puedes extraer de tu riqueza. Situaciones específicas se abordarán más adelante, por ejemplo en caso de que haya una cantidad muy sustancial de capital pendiente que no puede ser pagada en tu vida.",
    "fr":"Fournissez ici le montant total de votre richesse aujourd'hui. Incluez les biens immobiliers, les actions, les obligations, l'argent liquide et les autres actifs. Ne réduisez pas ce montant par la dette que vous devez. Le modèle suppose que le service de la dette est couvert par votre revenu actuel et, après votre retraite, dans la quantité que vous pouvez extraire de votre richesse. Des situations spécifiques seront abordées plus tard, par exemple en cas d'une très importante somme de capital en suspens qui ne peut pas être remboursée dans votre vie.",
    "de":"Geben Sie hier den Gesamtbetrag Ihres Vermögens zum heutigen Tag an. Enthalten sind Immobilien, Aktien, Anleihen, Bargeld und andere Vermögenswerte. Reduzieren Sie diesen Betrag nicht durch die Schulden, die Sie schulden. Das Modell geht davon aus, dass die Abzahlung der Schulden durch Ihr aktuelles Einkommen gedeckt ist und nach Ihrer Rente durch den Betrag, den Sie aus Ihrem Vermögen ziehen können. Spezielle Situationen werden später behandelt, z. B. im Fall einer sehr großen Summe an Kapital, die nicht in Ihrem Leben zurückgezahlt werden kann.",
    "it":"Fornisci qui il totale del tuo patrimonio odierno. Includi immobili, azioni, obbligazioni, denaro liquido e altri asset. Non riduci questo importo per il debito che devi. Il modello assume che il servizio del debito sia coperto dal tuo reddito attuale e, dopo il tuo pensionamento, nella quantità che puoi estrarre dal tuo patrimonio. Situazioni specifiche saranno affrontate più tardi, ad esempio nel caso di una notevole somma di capitale in sospeso che non può essere rimborsata nella tua vita.",
    "ja":"今日のあなたの富の合計金額を提供してください。不動産、株式、債券、現金、その他の資産を含めてください。借入金を差し引かないでください。モデルは、借入金の支払いが現在の収入でカバーされ、引退後に富から引き出せる金額でカバーされると仮定しています。特定の状況は後で対処されます。たとえば、生涯で返済できない非常に大きな金額の資本が残っている場合などです。",
    "pt":"Forneça aqui o montante total de sua riqueza hoje. Inclua imóveis, ações, títulos, dinheiro e outros ativos. Não reduza este montante pela dívida que você deve. O modelo assume que o serviço da dívida é coberto pelo seu rendimento atual e, após sua aposentadoria, na quantidade que você pode extrair de sua riqueza. Situações específicas serão abordadas mais tarde, por exemplo, no caso de uma quantia substancial de capital pendente que não pode ser paga em sua vida.",
    "ru":"Укажите здесь общую сумму вашего состояния на сегодня. Включите недвижимость, акции, облигации, наличные и другие активы. Не вычитайте из этой суммы сумму долга, которую вы должны. Модель предполагает, что обслуживание долга покрывается вашим текущим доходом и, после выхода на пенсию, в сумме, которую вы можете извлечь из своего состояния. Специальные ситуации будут рассмотрены позже, например, в случае очень большой суммы просроченного капитала, которая не может быть выплачена в течение вашей жизни.",
    "zh":"在这里提供你今天的总财富金额。包括房地产、股票、债券、现金和其他资产。不要减去你欠的债务。模型假设债务的偿还由你的现有收入和退休后可以从财富中提取的金额来覆盖。特定情况将在稍后处理，例如在有非常大额的资本无法在您的有生之年偿还的情况下。"
    })
liquidity_title = Verbiage(
    {
    "en":"Liquidity",
    "es":"Liquidez",
    "fr":"Liquidité",
    "de":"Liquidität",
    "it":"Liquidità",
    "ja":"流動性",
    "pt":"Liquidez",
    "ru":"Ликвидность",
    "zh":"流动性"
    })
liquidity_prompt = Verbiage(
    {
    "en":"Cash you keep aside.",
    "es":"Efectivo que mantienes aparte.",
    "fr":"Liquidités que vous gardez de côté.",
    "de":"Bargeld, das Sie beiseitelegen.",
    "it":"Liquidità che tieni da parte.",
    "ja":"別に取っておく現金です。",
    "pt":"Dinheiro que você mantém de lado.",
    "ru":"Наличные, которые вы оставляете в стороне.",
    "zh":"你另外留出的现金。"
    })
liquidity_cash_buffer = Verbiage(
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
liquidity_cash_buffer_help = Verbiage(
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
    "en":"Mix",
    "es":"Mezcla",
    "fr":"Mix",
    "de":"Mix",
    "it":"Mix",
    "ja":"ミックス",
    "pt":"Mix",
    "ru":"Микс",
    "zh":"混合"
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
    "en":"Returns",
    "es":"Rendimiento",
    "fr":"Rendement",
    "de":"Rendite",
    "it":"Rendita",
    "ja":"収益",
    "pt":"Rendimento",
    "ru":"Доходность",
    "zh":"收益"
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


_THINKING_MODE_LABELS: dict[str, Verbiage] = {
    "capital": goal_thinking_mode_capital,
    "income": goal_thinking_mode_income,
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
                    help=goal_kind_help,
                ),
                FieldSpec(
                    "goal.thinking_mode",
                    goal_thinking_mode_title,
                    "choice",
                    choices=("capital", "income"),
                    choice_labels=_THINKING_MODE_LABELS,
                    help=goal_thinking_mode_help,
                ),
                FieldSpec(
                    path="goal.target_income",
                    label=goal_target_income,
                    kind="amount",
                    #min=0,
                    when=goal_is_retire_when | goal_is_save_for_income,
                    help=goal_target_income_help,
                ),
                FieldSpec(
                    path="goal.years_to_retire",
                    label=goal_years_to_retire,
                    kind="int",
                    min=0,
                    when=goal_is_save_for_income,
                    help=goal_years_to_retire_help,
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
            ],
            default_next="liquidity",
        ),
        Step(
            id="liquidity",
            title=liquidity_title,
            prompt=liquidity_prompt,
            fields=[
                FieldSpec(
                    "liquidity.cash_buffer",
                    liquidity_cash_buffer,
                    "amount",
                    help=liquidity_cash_buffer_help,
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
