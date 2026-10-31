// See LSControlsWidget.h for this class's purpose, pattern and connections.

#include "LSControlsWidget.h"

#include "Components/Button.h"
#include "Components/TextBlock.h"

void ULSControlsWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();

	BackButton->OnClicked.AddDynamic(this, &ULSControlsWidget::HandleBack);

	// Set here and not in the layout, so this stays next to the code that defines the keys.
	ControlsText->SetText(NSLOCTEXT("LastSeed", "ControlsList",
		"Move: WASD / Left stick\n"
		"Look: Mouse / Right stick\n"
		"Jump, hold to glide as Dandelion: Space / A\n"
		"Slam as Stone Shell: Left Ctrl or Left Mouse / B\n"
		"Seed, Stone Shell, Dandelion: 1, 2, 3 / D-pad\n"
		"Cycle form: Q, E / LB, RB\n"
		"Pause: Esc / Start"));
}

void ULSControlsWidget::Open()
{
	SetVisibility(ESlateVisibility::Visible);
	BackButton->SetFocus();
}

void ULSControlsWidget::HandleBack()
{
	SetVisibility(ESlateVisibility::Collapsed);
	OnClosed.Broadcast();
}
