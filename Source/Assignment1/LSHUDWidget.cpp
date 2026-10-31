// See LSHUDWidget.h for this class's purpose, pattern and connections.

#include "LSHUDWidget.h"

#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "LSGameMode.h"
#include "LSLevelTypes.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

namespace
{
	FText GetFormDisplayName(ESeedForm Form)
	{
		switch (Form)
		{
		case ESeedForm::Stone:
			return NSLOCTEXT("LastSeed", "FormStone", "Stone Shell");
		case ESeedForm::Dandelion:
			return NSLOCTEXT("LastSeed", "FormDandelion", "Dandelion");
		default:
			return NSLOCTEXT("LastSeed", "FormSeed", "Seed");
		}
	}
}

void ULSHUDWidget::NativeConstruct()
{
	Super::NativeConstruct();

	URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	Restoration->OnNoteCollected.AddUniqueDynamic(this, &ULSHUDWidget::HandleNoteCollected);
	Restoration->OnRestorationChanged.AddUniqueDynamic(this, &ULSHUDWidget::HandleRestorationChanged);

	RefreshNotes();
	HandleRestorationChanged(Restoration->GetRestoration());
	ShowForm(ESeedForm::Seed);
	PromptText->SetRenderOpacity(0.f);
}

void ULSHUDWidget::SetBall(ASeedBall* Ball)
{
	Ball->OnFormChanged.AddUniqueDynamic(this, &ULSHUDWidget::HandleFormChanged);
	ShowForm(Ball->GetCurrentForm());
}

void ULSHUDWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (const ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		TimerText->SetText(LSFormatTime(GameMode->GetLevelTime()));
		PetalsText->SetText(FText::AsNumber(GameMode->GetGoldenPetalsCollected()));
	}

	if (PromptTimeRemaining > 0.f)
	{
		PromptTimeRemaining -= InDeltaTime;
		// Above the fade time this clamps to 1, so the text stays solid until only the fade time is left.
		PromptText->SetRenderOpacity(FMath::Clamp(PromptTimeRemaining / PromptFadeTime, 0.f, 1.f));
	}
}

void ULSHUDWidget::ShowPrompt(const FText& Message, float Duration)
{
	PromptText->SetText(Message);
	PromptTimeRemaining = Duration + PromptFadeTime;
	PromptText->SetRenderOpacity(1.f);
}

void ULSHUDWidget::HandleFormChanged(ESeedForm OldForm, ESeedForm NewForm)
{
	ShowForm(NewForm);
}

void ULSHUDWidget::ShowForm(ESeedForm Form)
{
	FormNameText->SetText(GetFormDisplayName(Form));

	if (const TObjectPtr<UTexture2D>* Icon = FormIcons.Find(Form))
	{
		FormIcon->SetBrushFromTexture(*Icon);
	}
}

void ULSHUDWidget::HandleNoteCollected(FVector Location)
{
	RefreshNotes();
}

void ULSHUDWidget::RefreshNotes()
{
	const URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	NotesText->SetText(FText::FromString(FString::Printf(TEXT("Life Notes %d/%d"),
		Restoration->GetNotesCollected(), Restoration->GetNotesTotal())));
}

void ULSHUDWidget::HandleRestorationChanged(float Restoration)
{
	RestorationBar->SetPercent(Restoration);
}
