// See LSGameMode.h for this class's purpose, pattern and connections.

#include "LSGameMode.h"

#include "AdaptiveMusicComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GoldenPetal.h"
#include "Kismet/GameplayStatics.h"
#include "KillVolume.h"
#include "LevelGoal.h"
#include "LevelSequence.h"
#include "LSGameInstance.h"
#include "LSPlayerController.h"
#include "Materials/MaterialInterface.h"
#include "MusicManager.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"
#include "Sound/SoundBase.h"
#include "TrailCrosswind.h"
#include "TutorialTrigger.h"
#include "Styling/CoreStyle.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	void EnableWildwoodRiverHazard(UWorld* World)
	{
		const UMaterialInterface* RiverMaterial = FindObject<UMaterialInterface>(nullptr,
			TEXT("/Game/Wildwood/Material/MI_River_01.MI_River_01"));
		if (!RiverMaterial)
		{
			return;
		}

		for (TActorIterator<AStaticMeshActor> River(World); River; ++River)
		{
			UStaticMeshComponent* Surface = River->GetStaticMeshComponent();
			if (Surface->GetMaterial(0) != RiverMaterial)
			{
				continue;
			}
			Surface->ComponentTags.AddUnique(ASeedBall::LethalWaterTag);
			// Replace the broad river fall triggers with contact at the surface.
			const FBox RiverBounds = Surface->Bounds.GetBox();
			for (TActorIterator<AKillVolume> Volume(World); Volume; ++Volume)
			{
				if (!Volume->LavaSurface && !Volume->SplashMaterial && Volume->BurnEffects.IsEmpty() && !Volume->BurnSound
					&& Volume->GetComponentsBoundingBox().Intersect(RiverBounds))
				{
					Volume->SetActorEnableCollision(false);
				}
			}
		}
	}

	struct FCreditSection
	{
		const TCHAR* Heading;
		const TCHAR* Text;
	};

	const FCreditSection CreditSections[] = {
		{ TEXT("Design and development"), TEXT("Howard Wilyman") },
		{ TEXT("Music"), TEXT("Scott Buckley\nA Dragon’s Lullaby · Juggernaut\n\nKevin MacLeod\nHeartwarming · Dark Standoff\n\nCreative Commons Attribution 4.0") },
		{ TEXT("Recorded sound"), TEXT("Barracuda1983 · Fission9 · Bini_trns\nmvVoiceActing · o_ciz · InspectorJ\nOldome · oscaraudiogeek · Kinoton\nAnthousai · dichardson · rykenn\nkingsrow · WavJunction.com\nHOGGanimation · K-Forces\nDanJFilms · michelcik\nmyLoop · follytowers · SamsterBirdies\nCinetony · Snudio_Records\nteadrinker · nilbul\n\nRecording credits and licenses\nAUDIO_CREDITS.md") },
		{ TEXT("Environment and effects"), TEXT("Wildwood · Lava Environments\nRocks Pack Demo\nPolytope Studio · StyleHex Studio\nSoftTofu") },
		{ TEXT("Illustrations"), TEXT("OpenAI") },
		{ TEXT("Voice performances"), TEXT("Heart Tree · Adam\nWitch · Kristen\nElevenLabs") },
		{ TEXT("Engine"), TEXT("Unreal Engine") },
	};

	struct FWildwoodEnding
	{
		~FWildwoodEnding()
		{
			if (Viewport.IsValid() && Player.IsValid() && Overlay.IsValid())
			{
				Viewport->RemoveViewportWidgetForPlayer(Player.Get(), Overlay.ToSharedRef());
			}
		}

		void AddOverlay(ULocalPlayer* LocalPlayer, UGameViewportClient* GameViewport)
		{
			Player = LocalPlayer;
			Viewport = GameViewport;
			const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
			const UObject* Font = LoadObject<UObject>(nullptr, TEXT("/Game/UI/Fonts/F_Wildwood.F_Wildwood"));
			const FSlateFontInfo TitleFont = Font ? FSlateFontInfo(Font, 56, TEXT("Heading")) : FCoreStyle::GetDefaultFontStyle("Bold", 56);
			const FSlateFontInfo RoleFont = Font ? FSlateFontInfo(Font, 24, TEXT("Heading")) : FCoreStyle::GetDefaultFontStyle("Bold", 24);
			const FSlateFontInfo NameFont = Font ? FSlateFontInfo(Font, 23, TEXT("Regular")) : FCoreStyle::GetDefaultFontStyle("Regular", 23);
			const FLinearColor Accent(0.91f, 0.78f, 0.52f);
			const TSharedRef<SVerticalBox> Roll = SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 44.f, 0.f, 70.f)
				[SNew(STextBlock).Text(INVTEXT("LAST SEED")).Font(TitleFont).ColorAndOpacity(Accent)];
			for (const FCreditSection& Section : CreditSections)
			{
				Roll->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 48.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(0.34f).VAlign(VAlign_Top).Padding(0.f, 0.f, 30.f, 0.f)
					[SNew(STextBlock).Text(FText::FromString(Section.Heading)).Font(RoleFont).ColorAndOpacity(Accent).AutoWrapText(true)]
					+ SHorizontalBox::Slot().FillWidth(0.66f).VAlign(VAlign_Top)
					[SNew(STextBlock).Text(FText::FromString(Section.Text)).Font(NameFont).AutoWrapText(true).LineHeightPercentage(1.35f)]
				];
			}
			Roll->AddSlot().AutoHeight().Padding(0.f, 48.f, 0.f, 150.f)
			[SNew(STextBlock).Text(INVTEXT("Thank you for playing")).Font(RoleFont).ColorAndOpacity(Accent)];
			SAssignNew(Overlay, SOverlay).Visibility(EVisibility::HitTestInvisible)
				+ SOverlay::Slot().VAlign(VAlign_Top)
				[
					SNew(SBox).HeightOverride(38.f)
					[SNew(SBorder).BorderImage(White).BorderBackgroundColor(FLinearColor::Black)]
				]
				+ SOverlay::Slot().VAlign(VAlign_Bottom)
				[
					SNew(SBox).HeightOverride(44.f)
					[SNew(SBorder).BorderImage(White).BorderBackgroundColor(FLinearColor::Black)]
				]
				+ SOverlay::Slot().VAlign(VAlign_Bottom).Padding(24.f, 0.f, 24.f, 9.f)
				[
					SAssignNew(Subtitle, STextBlock)
					.Text(NSLOCTEXT("LastSeed", "HeartTreeEnding", "You did it, little Seed. Look how far your roots have reached."))
					.Font(FCoreStyle::GetDefaultFontStyle("Bold", 20))
					.ColorAndOpacity(FLinearColor::White)
					.Justification(ETextJustify::Center)
					.AutoWrapText(true)
				]
				+ SOverlay::Slot()
				[SAssignNew(Black, SBorder).BorderImage(White).BorderBackgroundColor(FLinearColor::Black)]
				+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
				[
					SAssignNew(GameOver, STextBlock).Text(INVTEXT("GAME OVER")).Font(TitleFont).ColorAndOpacity(Accent)
				]
				+ SOverlay::Slot().HAlign(HAlign_Center).Padding(40.f, 55.f)
				[
					SNew(SBox).WidthOverride(900.f)
					[
						SAssignNew(Credits, SScrollBox)
						.Clipping(EWidgetClipping::ClipToBounds)
						.ScrollBarVisibility(EVisibility::Collapsed)
						+ SScrollBox::Slot()[Roll]
					]
				];
			Subtitle->SetRenderOpacity(0.f);
			Black->SetRenderOpacity(0.f);
			GameOver->SetRenderOpacity(0.f);
			Credits->SetRenderOpacity(0.f);
			GameViewport->AddViewportWidgetForPlayer(LocalPlayer, Overlay.ToSharedRef(), 100);
		}

		void ShowForest(float Elapsed, float VoiceTime, float FadeTime) const
		{
			const float CaptionIn = FMath::SmoothStep(VoiceTime - 0.2f, VoiceTime + 0.2f, Elapsed);
			const float CaptionOut = FMath::SmoothStep(FadeTime - 0.6f, FadeTime, Elapsed);
			Subtitle->SetRenderOpacity(CaptionIn * (1.f - CaptionOut));
			Black->SetRenderOpacity(FMath::SmoothStep(FadeTime, FadeTime + 1.8f, Elapsed));
		}

		bool ShowCredits(float Elapsed)
		{
			constexpr float CardSeconds = 3.5f;
			constexpr float RollSeconds = 36.f;
			constexpr float EndHold = 3.f;
			if (Elapsed < CardSeconds)
			{
				GameOver->SetRenderOpacity(FMath::SmoothStep(0.f, 0.6f, FMath::Min(Elapsed, CardSeconds - Elapsed)));
				return true;
			}
			GameOver->SetRenderOpacity(0.f);
			const float Time = Elapsed - CardSeconds;
			const float Alpha = FMath::Clamp((Time - 2.f) / RollSeconds, 0.f, 1.f);
			const float EndTime = 2.f + RollSeconds + EndHold;
			Credits->SetScrollOffset(Credits->GetScrollOffsetOfEnd() * Alpha);
			Credits->SetRenderOpacity(FMath::SmoothStep(0.f, 0.8f, FMath::Min(Time, EndTime - Time)));
			return Time < EndTime;
		}

		TWeakObjectPtr<ULocalPlayer> Player;
		TWeakObjectPtr<UGameViewportClient> Viewport;
		TSharedPtr<SOverlay> Overlay;
		TSharedPtr<SBorder> Black;
		TSharedPtr<SScrollBox> Credits;
		TSharedPtr<STextBlock> GameOver;
		TSharedPtr<STextBlock> Subtitle;
		bool bVoiceStarted = false;
	};
}

ALSGameMode::ALSGameMode()
{
	PrimaryActorTick.bCanEverTick = true;

	DefaultPawnClass = ASeedBall::StaticClass();
	PlayerControllerClass = ALSPlayerController::StaticClass();

	static ConstructorHelpers::FObjectFinder<UTexture2D> WitchArt(
		TEXT("/Game/LastSeed/Intro/EmberwoodFinale/T_LS_CastleWitchShock.T_LS_CastleWitchShock"));
	static ConstructorHelpers::FObjectFinder<USoundBase> WitchVoice(
		TEXT("/Game/LastSeed/Audio/VO_LS_EmberwoodWitchShock.VO_LS_EmberwoodWitchShock"));
	static ConstructorHelpers::FObjectFinder<UTexture2D> PlantingArt(
		TEXT("/Game/LastSeed/Intro/WitchExile/T_LS_PlantingSoil.T_LS_PlantingSoil"));
	static ConstructorHelpers::FObjectFinder<UTexture2D> ForestArt(
		TEXT("/Game/LastSeed/Intro/EmberwoodFinale/T_LS_WildwoodRestored.T_LS_WildwoodRestored"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> WitchMotion(
		TEXT("/Game/LastSeed/Intro/EmberwoodFinale/MI_LS_CastleWitchShock.MI_LS_CastleWitchShock"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> PlantingMotion(
		TEXT("/Game/LastSeed/Intro/EmberwoodFinale/MI_LS_SeedTakesRoot.MI_LS_SeedTakesRoot"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> ForestMotion(
		TEXT("/Game/LastSeed/Intro/EmberwoodFinale/MI_LS_WildwoodRestored.MI_LS_WildwoodRestored"));
	static ConstructorHelpers::FObjectFinder<USoundBase> ReturnMusic(
		TEXT("/Game/LastSeed/Audio/MUS_LS_WildwoodReturn.MUS_LS_WildwoodReturn"));
	RestoredArrivalMusic = ReturnMusic.Object;
	static ConstructorHelpers::FObjectFinder<USoundBase> HeartTreeVoice(
		TEXT("/Game/LastSeed/Audio/VO_LS_HeartTreeEnding.VO_LS_HeartTreeEnding"));
	HeartTreeEndingVoice = HeartTreeVoice.Object;

	if (WitchArt.Succeeded())
	{
		FLSIntroShot& Witch = EmberwoodFinaleShots.AddDefaulted_GetRef();
		Witch.Image = WitchArt.Object;
		Witch.MotionMaterial = WitchMotion.Object;
		Witch.Duration = 4.6f;
		Witch.FadeIn = 0.3f;
		Witch.StartZoom = 1.f;
		Witch.EndZoom = 1.055f;
		Witch.Caption = NSLOCTEXT("LastSeed", "EmberwoodWitchShock", "You crossed my fire? How are you still alive?");
		EmberwoodFinaleVoice = WitchVoice.Object;
	}
	if (PlantingArt.Succeeded() && ForestArt.Succeeded() && PlantingMotion.Succeeded() && ForestMotion.Succeeded())
	{
		FLSIntroShot& Planting = RestoredArrivalShots.AddDefaulted_GetRef();
		Planting.Image = PlantingArt.Object;
		Planting.MotionMaterial = PlantingMotion.Object;
		Planting.Duration = 3.2f;
		Planting.FadeIn = 0.f;

		FLSIntroShot& Forest = RestoredArrivalShots.AddDefaulted_GetRef();
		Forest.Image = ForestArt.Object;
		Forest.MotionMaterial = ForestMotion.Object;
		Forest.Duration = 8.f;
		Forest.FadeIn = 0.f;
	}
}

void ALSGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);

	// Read before any actor's BeginPlay, and cleared, so only the level opened by the burst arrives restored.
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		bRestoredArrival = GameInstance->bRestoredArrival;
		GameInstance->bRestoredArrival = false;
		// Level 1 starts with Seed alone; its flowers unlock the rest, which then travel on to Level 2.
		// The restored epilogue back in Wildwood is the end of a run, so it keeps the forms.
		if (!bRestoredArrival && UGameplayStatics::GetCurrentLevelName(this) == TEXT("L_Level1_Wildwood"))
		{
			GameInstance->ResetFormsForNewRun();
		}
	}
}

void ALSGameMode::BeginPlay()
{
	Super::BeginPlay();

	for (TActorIterator<AGoldenPetal> It(GetWorld()); It; ++It)
	{
		++GoldenPetalsTotal;
	}

	if (bRestoredArrival)
	{
		for (TActorIterator<ATrailCrosswind> It(GetWorld()); It; ++It)
		{
			It->SetActorTickEnabled(false);
		}
		if (const ALSPlayerController* PlayerController = GetLSPlayerController())
		{
			PlayerController->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::White, false);
		}
		GetWorldTimerManager().SetTimerForNextTick(this, &ALSGameMode::PlayRestoredArrival);
	}
	else if (UGameplayStatics::GetCurrentLevelName(this) == TEXT("L_Level1_Wildwood"))
	{
		EnableWildwoodRiverHazard(GetWorld());
		const FVector Trail2Crossing(-12450.0, -6860.0, 3170.0);
		const FRotator TrailHeading(0.0, 22.0, 0.0);
		const FVector UpperCrossing(-10740.0, -5360.0, 3170.0);
		const FRotator UpperTrailHeading(0.0, 49.0, 0.0);
		const FName SoftTrailEdge(TEXT("LS_SoftTrailEdge"));
		// Keep the river opening anchored to Trail 2 when designers move or copy gusts.
		for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		{
			if (!It->ActorHasTag(SoftTrailEdge))
			{
				continue;
			}
			const FVector Edge = It->GetActorLocation();
			const FVector Local = TrailHeading.UnrotateVector(Edge - Trail2Crossing);
			const FVector Upper = UpperTrailHeading.UnrotateVector(Edge - UpperCrossing);
			const bool bLowerRiverEdge = FMath::Abs(Local.X) < 1420.f && Local.Y > 275.f && Local.Y < 1150.f;
			const bool bUpperRiverEdge = Upper.X > -800.f && Upper.X < 2350.f && Upper.Y > 275.f && Upper.Y < 950.f;
			if (bLowerRiverEdge || bUpperRiverEdge)
			{
				It->SetActorEnableCollision(false);
			}
		}

		// shortcut: maps saved before the crosswind was placed need a fallback; remove when those maps are updated.
		if (!TActorIterator<ATrailCrosswind>(GetWorld()))
		{
			GetWorld()->SpawnActor<ATrailCrosswind>(Trail2Crossing, FRotator(0.0, 70.0, 0.0));
		}

		const FTransform WindApproach(FRotator(0.0, 12.0, 0.0), FVector(-13110.0, -7040.0, 3180.0));
		if (ATutorialTrigger* Warning = GetWorld()->SpawnActorDeferred<ATutorialTrigger>(ATutorialTrigger::StaticClass(), WindApproach))
		{
			Warning->ConfigurePrompt(NSLOCTEXT("LastSeed", "CrosswindWarningTitle", "WATCH OUT"),
				NSLOCTEXT("LastSeed", "CrosswindWarningBody", "Gusts can push you into the river. Cross when the wind dies down."),
				FVector(180.0, 520.0, 280.0));
			Warning->FinishSpawning(WindApproach);
		}
	}
}

void ALSGameMode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(WildwoodEndingTimer);
	Super::EndPlay(EndPlayReason);
}

void ALSGameMode::PlayRestoredArrival()
{
	if (ALSPlayerController* PlayerController = GetLSPlayerController())
	{
		if (APawn* Seed = PlayerController->GetPawn())
		{
			Seed->SetActorTickEnabled(false);
			Seed->SetActorHiddenInGame(true);
			Seed->SetActorEnableCollision(false);
			if (UPrimitiveComponent* Root = Cast<UPrimitiveComponent>(Seed->GetRootComponent()))
			{
				Root->SetSimulatePhysics(false);
			}
		}

		PlayerController->BeginWildwoodEpilogue();
		ULocalPlayer* LocalPlayer = PlayerController->GetLocalPlayer();
		UGameViewportClient* Viewport = LocalPlayer ? LocalPlayer->ViewportClient : nullptr;
		if (!Viewport)
		{
			PlayerController->ReturnToMainMenu();
			return;
		}

		// The authored Wildwood river shot keeps the stepping stones and the treetops in frame.
		const FVector Start(18728.1, 2777.1, 2525.4);
		const FVector End(18625.5, 3080.0, 2615.0);
		const FRotator StartAngle(14.7, 87.7, 0.0);
		const FRotator EndAngle(15.0, 89.0, 0.0);
		ACameraActor* Camera = GetWorld()->SpawnActor<ACameraActor>(Start, StartAngle);
		if (Camera)
		{
			Camera->GetCameraComponent()->SetFieldOfView(90.f);
			PlayerController->SetViewTarget(Camera);
		}
		// Give the live camera a few frames to settle behind the same white frame used for travel.
		APlayerCameraManager* CameraManager = PlayerController->PlayerCameraManager;
		CameraManager->SetManualCameraFade(1.f, FLinearColor::White, false);
		CameraManager->UpdateCamera(0.f);
		FTimerHandle RevealTimer;
		GetWorldTimerManager().SetTimer(RevealTimer, FTimerDelegate::CreateWeakLambda(CameraManager, [CameraManager]()
		{
			CameraManager->StartCameraFade(1.f, 0.f, 1.25f, FLinearColor::White, false, false);
		}), 0.25f, false);

		const TSharedRef<FWildwoodEnding> Ending = MakeShared<FWildwoodEnding>();
		Ending->AddOverlay(LocalPlayer, Viewport);
		const double BeganAt = GetWorld()->GetTimeSeconds();
		constexpr float VoiceTime = 7.5f;
		const float FadeTime = VoiceTime + FMath::Max(4.f, HeartTreeEndingVoice ? HeartTreeEndingVoice->GetDuration() : 0.f) + 2.2f;
		GetWorldTimerManager().SetTimer(WildwoodEndingTimer, FTimerDelegate::CreateWeakLambda(this,
			[this, PlayerController = TWeakObjectPtr<ALSPlayerController>(PlayerController),
				Camera = TWeakObjectPtr<ACameraActor>(Camera), Ending, BeganAt, FadeTime, Start, End, StartAngle, EndAngle]()
			{
				const float Elapsed = GetWorld()->GetTimeSeconds() - BeganAt;
				if (Elapsed < FadeTime + 1.8f)
				{
					if (Camera.IsValid())
					{
						const float Move = FMath::SmoothStep(0.f, FadeTime, Elapsed);
						Camera->SetActorLocationAndRotation(FMath::Lerp(Start, End, Move),
							FMath::Lerp(StartAngle, EndAngle, Move));
					}
					if (Elapsed >= VoiceTime && !Ending->bVoiceStarted)
					{
						Ending->bVoiceStarted = true;
						UGameplayStatics::PlaySound2D(this, HeartTreeEndingVoice, 1.05f);
					}
					Ending->ShowForest(Elapsed, VoiceTime, FadeTime);
					return;
				}

				// A slow frame can step straight past the tail of the fade.
				Ending->Black->SetRenderOpacity(1.f);
				Ending->Subtitle->SetRenderOpacity(0.f);
				if (!Ending->ShowCredits(Elapsed - FadeTime - 1.8f))
				{
					GetWorldTimerManager().PauseTimer(WildwoodEndingTimer);
					if (PlayerController.IsValid())
					{
						PlayerController->ReturnToMainMenu();
					}
				}
			}), 1.f / 60.f, true);
	}
}

void ALSGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// This doesn't tick while the game is paused, so menus and story cards don't add to the time.
	if (bTimerRunning && !bLevelComplete)
	{
		LevelTime += DeltaSeconds;
	}
}

void ALSGameMode::RestartPlayer(AController* NewPlayer)
{
	Super::RestartPlayer(NewPlayer);

	if (ASeedBall* Ball = Cast<ASeedBall>(NewPlayer->GetPawn()))
	{
		Ball->OnDied.AddUniqueDynamic(this, &ALSGameMode::HandleBallDied);

		// Home from Emberwood: Seed lands just before where it was planted (ALevelGoal), looking back over the healed trail.
		// Not in the goal itself, which the regrown Heart Tree's leaves now crowd.
		if (bRestoredArrival)
		{
			for (TActorIterator<ALevelGoal> It(GetWorld()); It; ++It)
			{
				const FVector Home = It->GetActorLocation() - It->GetActorForwardVector() * 700.f + FVector(0.f, 0.f, 60.f);
				Ball->TeleportBall(Home);
				Ball->SetCheckpoint(Home);
				NewPlayer->SetControlRotation(FRotator(-10.f, It->GetActorRotation().Yaw + 180.f, 0.f));
				break;
			}
		}
	}
}

void ALSGameMode::HandleBallDied()
{
	++Deaths;
}

void ALSGameMode::AddGoldenPetal()
{
	++GoldenPetalsCollected;
}

ALSPlayerController* ALSGameMode::GetLSPlayerController() const
{
	return Cast<ALSPlayerController>(GetWorld()->GetFirstPlayerController());
}

FLSLevelResult ALSGameMode::BuildResult(const ALevelGoal* Goal) const
{
	const URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();

	FLSLevelResult Result;
	Result.TimeSeconds = LevelTime;
	Result.ParTimeSeconds = Goal->ParTimeSeconds;
	Result.Deaths = Deaths;
	Result.NotesCollected = Restoration->GetNotesCollected();
	Result.NotesTotal = Restoration->GetNotesTotal();
	Result.PetalsCollected = GoldenPetalsCollected;
	Result.PetalsTotal = GoldenPetalsTotal;
	Result.PetalsRequired = Goal->RequiredPetals;

	Result.bAllNotes = Result.NotesCollected >= Result.NotesTotal;
	Result.bUnderPar = Result.TimeSeconds <= Result.ParTimeSeconds;
	Result.bEnoughPetals = Result.PetalsCollected >= Result.PetalsRequired;

	// Finishing earns 1 star and all notes earns 2. The third needs par and petals as well as all notes.
	if (!Result.bAllNotes)
	{
		Result.Stars = 1;
	}
	else
	{
		Result.Stars = Result.bUnderPar && Result.bEnoughPetals ? 3 : 2;
	}
	return Result;
}

void ALSGameMode::CompleteLevel(ALevelGoal* Goal)
{
	if (bLevelComplete)
	{
		return;
	}
	bLevelComplete = true;
	CompletedGoal = Goal;
	LastResult = BuildResult(Goal);

	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		// Saved now, so quitting during the ending can't lose the result.
		GameInstance->RecordLevelResult(FName(UGameplayStatics::GetCurrentLevelName(this)), LastResult);
	}

	OnLevelCompleted.Broadcast();

	if (ALSPlayerController* PlayerController = GetLSPlayerController())
	{
		const bool bEnergyFinale = Goal->bEnergyFinale;
		const bool bWitchReaction = bEnergyFinale && !EmberwoodFinaleShots.IsEmpty();
		TArray<FLSIntroShot> Shots = bWitchReaction ? EmberwoodFinaleShots : Goal->TravelShots;
		USoundBase* Voice = bWitchReaction ? EmberwoodFinaleVoice.Get() : nullptr;
		if (Voice)
		{
			// Keep the witch visible through the line, then leave time for the existing fade.
			Shots.Last().Duration = FMath::Max(Shots.Last().Duration, Voice->GetDuration() + 1.75f);
		}
		if (!Shots.IsEmpty() && !Goal->NextLevel.IsNull())
		{
			TWeakObjectPtr<UAdaptiveMusicComponent> DialogueMusic;
			if (bEnergyFinale)
			{
				const TActorIterator<AMusicManager> MusicManager(GetWorld());
				if (MusicManager)
				{
					DialogueMusic = MusicManager->FindComponentByClass<UAdaptiveMusicComponent>();
				}
				if (DialogueMusic.IsValid())
				{
					DialogueMusic->SetDialogueDucking(true);
				}
			}
			// The energy finale comes back to the game after the shots, so the burst plays in the world.
			PlayerController->PlayIntro(Shots, bEnergyFinale ? nullptr : Goal->TravelAudio.Get(), Voice,
				bEnergyFinale ? ELSIntroTransition::Gameplay : ELSIntroTransition::Travel, FVector::ZeroVector,
				[this, Goal, PlayerController, bEnergyFinale, DialogueMusic]()
				{
					if (DialogueMusic.IsValid())
					{
						DialogueMusic->SetDialogueDucking(false);
					}
					if (!bEnergyFinale)
					{
						ContinueAfterResults();
						return;
					}
					Goal->PlayEnergyBurst(Cast<ASeedBall>(PlayerController->GetPawn()), [this, PlayerController]()
					{
						if (RestoredArrivalShots.IsEmpty())
						{
							ContinueAfterResults();
							return;
						}

						// Play the illustrated return while Emberwood is still loaded. Travel on the closing white frame.
						PlayerController->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::White, false);
						PlayerController->PlayIntro(RestoredArrivalShots, RestoredArrivalMusic, nullptr,
							ELSIntroTransition::RestoredArrival, FVector::ZeroVector, [this]() { ContinueAfterResults(); });
					});
				});
			return;
		}
		PlayerController->PlayStory(Goal->EndingSequence, Goal->EndingCards, [this, PlayerController]()
		{
			PlayerController->ShowResults(LastResult);
		});
	}
}

void ALSGameMode::ContinueAfterResults()
{
	if (!CompletedGoal->NextLevel.IsNull())
	{
		if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
		{
			GameInstance->bRestoredArrival = CompletedGoal->bEnergyFinale;
		}
		UGameplayStatics::OpenLevelBySoftObjectPtr(this, CompletedGoal->NextLevel);
		return;
	}

	// No next level means this is the last one, so the credits play and then the menu opens.
	if (ALSPlayerController* PlayerController = GetLSPlayerController())
	{
		PlayerController->CloseMenu();
		PlayerController->PlayStory(nullptr, CompletedGoal->CreditsCards, [PlayerController]()
		{
			PlayerController->ReturnToMainMenu();
		});
	}
}

void ALSGameMode::RetryLevel()
{
	UGameplayStatics::OpenLevel(this, FName(UGameplayStatics::GetCurrentLevelName(this)));
}
