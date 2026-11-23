// See LSHUDWidget.h for this class's purpose, pattern and connections.

#include "LSHUDWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
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
	// Emberwood's bar fills with the energy Seed carries home, not with the forest's healing.
	if (UTextBlock* BarLabel = Cast<UTextBlock>(GetWidgetFromName(TEXT("RestorationLabel"))); BarLabel && bCountsEnergy)
	{
		BarLabel->SetText(NSLOCTEXT("LastSeed", "EnergyBar", "ENERGY"));
	}
	if (UTextBlock* Heading = Cast<UTextBlock>(GetWidgetFromName(TEXT("QuestHeading"))); Heading && bCountsEnergy)
	{
		Heading->SetText(NSLOCTEXT("LastSeed", "EnergyQuest", "GATHER THE ENERGY"));
	}
	if (bCountsEnergy)
	{
		BuildEnergyEffects();
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

	if (EnergyGlow)
	{
		TickEnergyEffects(InDeltaTime);
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
	ShowHint(bCountsEnergy ? NSLOCTEXT("LastSeed", "HintEmber", "EMBERWOOD GUIDE") : NSLOCTEXT("LastSeed", "Hint", "FOREST GUIDE"),
		FText::GetEmpty(), Message, Duration);
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
	if (EnergyGlow)
	{
		// Surges, and throws a fistful of sparks off the bar.
		EnergyPulse = 1.f;
		const float FillWidth = BarWidth * RestorationBar->GetPercent();
		for (int32 Index = 0; Index < 10; ++Index)
		{
			SpawnEnergySpark(FillWidth);
		}
	}
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

namespace
{
	// The energy orbs' own green, so the bar reads as the power Seed is carrying.
	const FLinearColor EnergyColour(0.45f, 1.f, 0.4f);
	constexpr int32 EnergySparkPool = 24;
	// Seconds a pickup's surge takes to settle back.
	constexpr float EnergyPulseSeconds = 1.6f;
}

void ULSHUDWidget::BuildEnergyEffects()
{
	// NativeConstruct runs again each time the HUD returns to the screen; build the effects only once.
	if (EnergyGlow)
	{
		return;
	}
	UTexture2D* GlowTexture = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/Textures/T_UI_Glow.T_UI_Glow"));
	UCanvasPanel* Canvas = Cast<UCanvasPanel>(RestorationBar->GetParent());
	UCanvasPanelSlot* BarSlot = Cast<UCanvasPanelSlot>(RestorationBar->Slot);
	if (!GlowTexture || !Canvas || !BarSlot)
	{
		return;
	}

	// A thicker line than the forest's, so the energy reads as a charged beam. It grows downward from its top.
	BarSlot->SetSize(FVector2D(BarSlot->GetSize().X, 5.f));
	const FVector2D Size = BarSlot->GetSize();
	const FVector2D Alignment = BarSlot->GetAlignment();
	BarWidth = Size.X;
	BarOrigin = BarSlot->GetPosition() - Alignment * Size + FVector2D(0.f, Size.Y * 0.5f);
	RestorationBar->SetFillColorAndOpacity(EnergyColour);

	auto AddImage = [&](int32 ZOrder, const FVector2D& ImageAlignment)
	{
		UImage* Image = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass());
		Image->SetBrushFromTexture(GlowTexture);
		Image->SetColorAndOpacity(EnergyColour);
		Image->SetVisibility(ESlateVisibility::Collapsed);
		UCanvasPanelSlot* ImageSlot = Canvas->AddChildToCanvas(Image);
		ImageSlot->SetAnchors(BarSlot->GetAnchors());
		ImageSlot->SetAlignment(ImageAlignment);
		ImageSlot->SetZOrder(BarSlot->GetZOrder() + ZOrder);
		return Image;
	};
	// The glow sits behind the bar, the tip and sparks in front of it.
	EnergyGlow = AddImage(-1, FVector2D(0.f, 0.5f));
	// Drawn as a box: the dot's two halves cap the ends and its bright middle column stretches between them, so the
	// glow runs evenly along the whole fill instead of bunching in its middle.
	FSlateBrush GlowBrush = EnergyGlow->GetBrush();
	GlowBrush.DrawAs = ESlateBrushDrawType::Box;
	GlowBrush.Margin = FMargin(0.5f, 0.f);
	GlowBrush.ImageSize = FVector2D(24.f, 24.f);
	EnergyGlow->SetBrush(GlowBrush);
	EnergyTip = AddImage(1, FVector2D(0.5f, 0.5f));
	EnergyTip->SetColorAndOpacity(FMath::Lerp(EnergyColour, FLinearColor::White, 0.6f));
	for (int32 Index = 0; Index < EnergySparkPool; ++Index)
	{
		UImage* Spark = AddImage(1, FVector2D(0.5f, 0.5f));
		Spark->SetColorAndOpacity(FMath::Lerp(FLinearColor(0.6f, 1.f, 0.3f), FLinearColor(1.f, 1.f, 0.6f), FMath::FRand()));
		EnergySparks.Add(Spark);
		SparkVelocities.Add(FVector2D::ZeroVector);
		SparkAges.Add(0.f);
		SparkLifetimes.Add(1.f);
	}
}

void ULSHUDWidget::SpawnEnergySpark(float FillWidth)
{
	if (FillWidth <= 0.f)
	{
		return;
	}
	const int32 Index = EnergySparks.IndexOfByPredicate([](const UImage* Spark) { return !Spark->IsVisible(); });
	if (Index == INDEX_NONE)
	{
		return;
	}
	UImage* Spark = EnergySparks[Index];
	UCanvasPanelSlot* SparkSlot = Cast<UCanvasPanelSlot>(Spark->Slot);
	// Most sparks fly off near the tip, where the power is building.
	SparkSlot->SetPosition(BarOrigin + FVector2D(FillWidth * FMath::Sqrt(FMath::FRand()), 0.f));
	const float Size = FMath::FRandRange(12.f, 22.f);
	SparkSlot->SetSize(FVector2D(Size, Size));
	SparkVelocities[Index] = FVector2D(FMath::FRandRange(-45.f, 45.f), FMath::FRandRange(-150.f, -50.f));
	SparkAges[Index] = 0.f;
	SparkLifetimes[Index] = FMath::FRandRange(0.45f, 0.9f);
	Spark->SetRenderScale(FVector2D(1.f, 1.f));
	Spark->SetRenderOpacity(1.f);
	Spark->SetVisibility(ESlateVisibility::HitTestInvisible);
}

void ULSHUDWidget::TickEnergyEffects(float DeltaSeconds)
{
	EnergyTime += DeltaSeconds;
	EnergyPulse = FMath::Max(EnergyPulse - DeltaSeconds / EnergyPulseSeconds, 0.f);
	const float Pulse = FMath::SmoothStep(0.f, 1.f, EnergyPulse);
	const float Breath = 0.5f + 0.5f * FMath::Sin(EnergyTime * 2.6f);
	const float FillWidth = BarWidth * RestorationBar->GetPercent();
	const ESlateVisibility Shown = FillWidth > 0.f ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed;

	RestorationBar->SetFillColorAndOpacity(FMath::Lerp(EnergyColour, FLinearColor::White, 0.1f * Breath + 0.5f * Pulse));

	EnergyGlow->SetVisibility(Shown);
	UCanvasPanelSlot* GlowSlot = Cast<UCanvasPanelSlot>(EnergyGlow->Slot);
	GlowSlot->SetPosition(BarOrigin - FVector2D(12.f, 0.f));
	GlowSlot->SetSize(FVector2D(FillWidth + 24.f, 60.f + 14.f * Breath + 40.f * Pulse));
	EnergyGlow->SetRenderOpacity(FMath::Min(0.75f + 0.15f * Breath + 0.25f * Pulse, 1.f));

	// The tip crackles: a new size and brightness every frame.
	EnergyTip->SetVisibility(Shown);
	UCanvasPanelSlot* TipSlot = Cast<UCanvasPanelSlot>(EnergyTip->Slot);
	const float TipSize = 30.f + 12.f * FMath::FRand() + 30.f * Pulse;
	TipSlot->SetPosition(BarOrigin + FVector2D(FillWidth, 0.f));
	TipSlot->SetSize(FVector2D(TipSize, TipSize));
	EnergyTip->SetRenderOpacity(FMath::FRandRange(0.65f, 1.f));

	SparkCountdown -= DeltaSeconds;
	if (SparkCountdown <= 0.f)
	{
		SpawnEnergySpark(FillWidth);
		SparkCountdown = FMath::FRandRange(0.5f, 1.5f) / (8.f + 50.f * Pulse);
	}

	for (int32 Index = 0; Index < EnergySparks.Num(); ++Index)
	{
		UImage* Spark = EnergySparks[Index];
		if (!Spark->IsVisible())
		{
			continue;
		}
		SparkAges[Index] += DeltaSeconds;
		const float Left = 1.f - SparkAges[Index] / SparkLifetimes[Index];
		if (Left <= 0.f)
		{
			Spark->SetVisibility(ESlateVisibility::Collapsed);
			continue;
		}
		// They leap up off the bar, slow, and wink out.
		SparkVelocities[Index].Y += 160.f * DeltaSeconds;
		UCanvasPanelSlot* SparkSlot = Cast<UCanvasPanelSlot>(Spark->Slot);
		SparkSlot->SetPosition(SparkSlot->GetPosition() + SparkVelocities[Index] * DeltaSeconds);
		Spark->SetRenderScale(FVector2D(Left, Left));
		Spark->SetRenderOpacity(Left * FMath::FRandRange(0.7f, 1.f));
	}
}
