// See LSStoryCardWidget.h for this class's purpose, pattern and connections.

#include "LSStoryCardWidget.h"

#include "Components/Button.h"
#include "Components/TextBlock.h"

void ULSStoryCardWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	NextButton->OnClicked.AddDynamic(this, &ULSStoryCardWidget::HandleNext);
}

void ULSStoryCardWidget::NativeConstruct()
{
	Super::NativeConstruct();

	NextButton->SetFocus();
}

void ULSStoryCardWidget::ShowCards(const TArray<FText>& InCards)
{
	Cards = InCards;
	CardIndex = 0;
	CardText->SetText(Cards[0]);
}

void ULSStoryCardWidget::HandleNext()
{
	++CardIndex;
	if (Cards.IsValidIndex(CardIndex))
	{
		CardText->SetText(Cards[CardIndex]);
	}
	else
	{
		OnFinished.Broadcast();
	}
}
