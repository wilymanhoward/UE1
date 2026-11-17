// See LSControlsWidget.h for this class's purpose, pattern and connections.

#include "LSControlsWidget.h"

#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "LSGameInstance.h"

void ULSControlsWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	BackButton->OnClicked.AddDynamic(this, &ULSControlsWidget::HandleBack);

}

void ULSControlsWidget::Open()
{
	FString Controls = TEXT("W A S D / LEFT STICK     Roll\n\nMOUSE / RIGHT STICK     Look around\n\nSPACE / A     Jump\n\nESC / START     Pause");
	if (const ULSGameInstance* GI = GetGameInstance<ULSGameInstance>())
	{
		if (GI->IsFormUnlocked(ESeedForm::Stone))
			Controls += TEXT("\n\n2 / D-PAD LEFT     Stone Shell\nLEFT CTRL / LEFT MOUSE / B     Slam");
		if (GI->IsFormUnlocked(ESeedForm::Dandelion))
			Controls += TEXT("\n\n3 / D-PAD RIGHT     Dandelion\nHOLD SPACE / A     Glide");
		if (GI->IsFormUnlocked(ESeedForm::Stone) || GI->IsFormUnlocked(ESeedForm::Dandelion))
			Controls += TEXT("\n\n1 / D-PAD UP     Seed\nQ E / LB RB     Cycle unlocked forms");
	}
	ControlsText->SetText(FText::FromString(Controls));
	SetVisibility(ESlateVisibility::Visible);
	BackButton->SetFocus();
}

void ULSControlsWidget::HandleBack()
{
	SetVisibility(ESlateVisibility::Collapsed);
	OnClosed.Broadcast();
}
