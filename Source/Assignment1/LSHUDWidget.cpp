// See LSHUDWidget.h for this class's purpose, pattern and connections.

#include "LSHUDWidget.h"

#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/TextBlock.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "LevelGoal.h"
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

	for (TActorIterator<ALevelGoal> It(GetWorld()); It; ++It)
	{
		bCountsEnergy |= It->bEnergyFinale;
	}
	RefreshNotes();
	HandleRestorationChanged(Restoration->GetRestoration());
	ShowForm(ESeedForm::Seed);
	PromptText->SetRenderOpacity(0.f);
	if (PromptPanel) PromptPanel->SetRenderOpacity(0.f);
	if (NoticePanel) NoticePanel->SetRenderOpacity(0.f);
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
		(PromptPanel ? PromptPanel.Get() : PromptText.Get())->SetRenderOpacity(FMath::Clamp(PromptTimeRemaining / PromptFadeTime, 0.f, 1.f));
	}
	if (NoticeTimeRemaining > 0.f && NoticePanel)
	{
		NoticeTimeRemaining -= InDeltaTime;
		NoticePanel->SetRenderOpacity(FMath::Clamp(NoticeTimeRemaining / PromptFadeTime, 0.f, 1.f));
	}
}

void ULSHUDWidget::ShowPrompt(const FText& Message, float Duration)
{
	ShowHint(NSLOCTEXT("LastSeed", "Hint", "FOREST GUIDE"), FText::GetEmpty(), Message, Duration);
}

void ULSHUDWidget::ShowHint(const FText& Title, const FText& Keys, const FText& Message, float Duration)
{
	if (PromptTitleText) PromptTitleText->SetText(Title);
	if (PromptKeyText) PromptKeyText->SetText(Keys);
	PromptText->SetText(Message);
	PromptTimeRemaining = Duration > 0.f ? Duration + PromptFadeTime : -1.f;
	PromptText->SetRenderOpacity(1.f);
	if (PromptPanel) PromptPanel->SetRenderOpacity(1.f);
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
	if (NoticePanel && NoticeText)
	{
		const URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
		const bool bFull = Restoration->GetNotesCollected() >= Restoration->GetNotesTotal();
		NoticeText->SetText(!bCountsEnergy ? NSLOCTEXT("LastSeed", "NoteObtained", "+1 LIFE NOTE   /   The forest stirs")
			: bFull ? NSLOCTEXT("LastSeed", "EnergyFull", "ENERGY FULL   /   Reach the castle ruins")
			: NSLOCTEXT("LastSeed", "EnergyObtained", "+1 ENERGY   /   Seed glows brighter"));
		NoticeTimeRemaining = 4.f;
		NoticePanel->SetRenderOpacity(1.f);
	}
}

void ULSHUDWidget::RefreshNotes()
{
	const URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	NotesText->SetText(FText::FromString(FString::Printf(TEXT("%s %d/%d"), bCountsEnergy ? TEXT("Energy") : TEXT("Life Notes"),
		Restoration->GetNotesCollected(), Restoration->GetNotesTotal())));
}

void ULSHUDWidget::HandleRestorationChanged(float Restoration)
{
	RestorationBar->SetPercent(Restoration);
	// Restoring a whole level at once (home from Emberwood) collects its notes without a collect event.
	RefreshNotes();
}
