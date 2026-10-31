// See LSResultsWidget.h for this class's purpose and connections.

#include "LSResultsWidget.h"

#include "Components/Button.h"
#include "Components/Image.h"
#include "Components/TextBlock.h"
#include "Engine/World.h"
#include "LSGameMode.h"

namespace
{
	FText MakeCondition(const FString& Description, bool bMet)
	{
		return FText::FromString(FString::Printf(TEXT("%s: %s"), *Description, bMet ? TEXT("Done") : TEXT("Missed")));
	}
}

void ULSResultsWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	NextButton->OnClicked.AddDynamic(this, &ULSResultsWidget::HandleNext);
	RetryButton->OnClicked.AddDynamic(this, &ULSResultsWidget::HandleRetry);
}

void ULSResultsWidget::NativeConstruct()
{
	Super::NativeConstruct();

	NextButton->SetFocus();
}

void ULSResultsWidget::ShowResult(const FLSLevelResult& Result)
{
	Star1->SetColorAndOpacity(Result.Stars >= 1 ? EarnedStarColor : MissedStarColor);
	Star2->SetColorAndOpacity(Result.Stars >= 2 ? EarnedStarColor : MissedStarColor);
	Star3->SetColorAndOpacity(Result.Stars >= 3 ? EarnedStarColor : MissedStarColor);

	TimeText->SetText(LSFormatTime(Result.TimeSeconds));
	NotesText->SetText(FText::FromString(FString::Printf(TEXT("%d/%d"), Result.NotesCollected, Result.NotesTotal)));
	PetalsText->SetText(FText::FromString(FString::Printf(TEXT("%d/%d"), Result.PetalsCollected, Result.PetalsTotal)));
	DeathsText->SetText(FText::AsNumber(Result.Deaths));

	NotesConditionText->SetText(MakeCondition(TEXT("All Life Notes"), Result.bAllNotes));
	ParConditionText->SetText(MakeCondition(
		FString::Printf(TEXT("Under %s"), *LSFormatTime(Result.ParTimeSeconds).ToString()), Result.bUnderPar));
	PetalsConditionText->SetText(MakeCondition(
		FString::Printf(TEXT("%d Golden Petals"), Result.PetalsRequired), Result.bEnoughPetals));
}

void ULSResultsWidget::HandleNext()
{
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->ContinueAfterResults();
	}
}

void ULSResultsWidget::HandleRetry()
{
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->RetryLevel();
	}
}
