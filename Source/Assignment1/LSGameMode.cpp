// See LSGameMode.h for this class's purpose, pattern and connections.

#include "LSGameMode.h"

#include "AdaptiveMusicComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GoldenPetal.h"
#include "Kismet/GameplayStatics.h"
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
#include "Styling/CoreStyle.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
	struct FEndingCard
	{
		const TCHAR* Heading;
		const TCHAR* Text;
		float Seconds;
	};

	const FEndingCard EndingCards[] = {
		{ TEXT("Game Over"), TEXT(""), 3.5f },
		{ TEXT("Last Seed"), TEXT("Design and development\nHoward Wilyman"), 5.f },
		{ TEXT("Music"), TEXT("Scott Buckley · A Dragon’s Lullaby, Juggernaut\nKevin MacLeod · Heartwarming, Dark Standoff\nCreative Commons Attribution 4.0"), 7.f },
		{ TEXT("Recorded sound"), TEXT("Barracuda1983 · Fission9 · Bini_trns\nmvVoiceActing · o_ciz · InspectorJ\nOldome · oscaraudiogeek · Kinoton\nAnthousai · dichardson · rykenn"), 7.f },
		{ TEXT("Recorded sound"), TEXT("kingsrow · WavJunction.com · HOGGanimation\nK-Forces · DanJFilms · michelcik\nmyLoop · follytowers · SamsterBirdies\nFull recording and license details in AUDIO_CREDITS.md"), 7.f },
		{ TEXT("Environment and effects"), TEXT("Wildwood · Lava Environments · Rocks Pack Demo\nAdditional assets · Polytope Studio, StyleHex Studio, SoftTofu"), 7.f },
		{ TEXT("Illustrations and voices"), TEXT("Cutscene illustrations · OpenAI\nHeart Tree · Adam    /    Witch · Kristen (ElevenLabs)\nMade with Unreal Engine"), 7.f },
		{ TEXT("Thank you for playing"), TEXT(""), 3.f },
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
				+ SOverlay::Slot().VAlign(VAlign_Center).Padding(24.f)
				[
					SAssignNew(Credits, SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
					[
						SAssignNew(Heading, STextBlock)
						.Font(FCoreStyle::GetDefaultFontStyle("Bold", 40))
						.ColorAndOpacity(FLinearColor(0.95f, 0.82f, 0.56f))
						.Justification(ETextJustify::Center)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f)
					[
						SAssignNew(Body, STextBlock)
						.Font(FCoreStyle::GetDefaultFontStyle("Regular", 19))
						.Justification(ETextJustify::Center)
						.AutoWrapText(true)
						.LineHeightPercentage(1.35f)
					]
				];
			Subtitle->SetRenderOpacity(0.f);
			Black->SetRenderOpacity(0.f);
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
			for (int32 Index = 0; Index < UE_ARRAY_COUNT(EndingCards); ++Index)
			{
				const FEndingCard& Card = EndingCards[Index];
				if (Elapsed < Card.Seconds)
				{
					if (Index != ActiveCard)
					{
						Heading->SetText(FText::FromString(Card.Heading));
						Body->SetText(FText::FromString(Card.Text));
						Body->SetVisibility(*Card.Text ? EVisibility::HitTestInvisible : EVisibility::Collapsed);
						ActiveCard = Index;
					}
					Credits->SetRenderOpacity(FMath::SmoothStep(0.f, 0.5f,
						FMath::Min(Elapsed, Card.Seconds - Elapsed)));
					return true;
				}
				Elapsed -= Card.Seconds;
			}
			return false;
		}

		TWeakObjectPtr<ULocalPlayer> Player;
		TWeakObjectPtr<UGameViewportClient> Viewport;
		TSharedPtr<SOverlay> Overlay;
		TSharedPtr<SBorder> Black;
		TSharedPtr<SVerticalBox> Credits;
		TSharedPtr<STextBlock> Heading;
		TSharedPtr<STextBlock> Body;
		TSharedPtr<STextBlock> Subtitle;
		int32 ActiveCard = INDEX_NONE;
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
		if (const ALSPlayerController* PlayerController = GetLSPlayerController())
		{
			PlayerController->PlayerCameraManager->SetManualCameraFade(1.f, FLinearColor::White, false);
		}
		GetWorldTimerManager().SetTimerForNextTick(this, &ALSGameMode::PlayRestoredArrival);
	}
	else if (UGameplayStatics::GetCurrentLevelName(this) == TEXT("L_Level1_Wildwood"))
	{
		// This stretch of Trail 2 is before the Stone Shell pickup, with the river to the trail's right.
		GetWorld()->SpawnActor<ATrailCrosswind>(FVector(-12450.0, -6860.0, 3170.0), FRotator(0.0, 70.0, 0.0));
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
