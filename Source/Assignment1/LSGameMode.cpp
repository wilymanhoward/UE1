// See LSGameMode.h for this class's purpose, pattern and connections.

#include "LSGameMode.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GoldenPetal.h"
#include "Kismet/GameplayStatics.h"
#include "LevelGoal.h"
#include "LevelSequence.h"
#include "LSGameInstance.h"
#include "LSPlayerController.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

ALSGameMode::ALSGameMode()
{
	PrimaryActorTick.bCanEverTick = true;

	DefaultPawnClass = ASeedBall::StaticClass();
	PlayerControllerClass = ALSPlayerController::StaticClass();
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
		if (ALSPlayerController* PlayerController = GetLSPlayerController())
		{
			// Continues the burst's white flash, clearing onto the healed forest.
			PlayerController->PlayerCameraManager->StartCameraFade(1.f, 0.f, 2.5f, FLinearColor::White, false, false);
			FTimerHandle PromptTimer;
			GetWorldTimerManager().SetTimer(PromptTimer, FTimerDelegate::CreateWeakLambda(PlayerController, [PlayerController]()
			{
				PlayerController->ShowPrompt(NSLOCTEXT("LastSeed", "RestoredArrival",
					"The energy flows home. Wildwood is whole again."), 8.f);
			}), 2.5f, false);
		}
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
		if (!Goal->TravelShots.IsEmpty() && !Goal->NextLevel.IsNull())
		{
			// The energy finale comes back to the game after the shots, so the burst plays in the world.
			const bool bEnergyFinale = Goal->bEnergyFinale;
			PlayerController->PlayIntro(Goal->TravelShots, Goal->TravelAudio, nullptr,
				bEnergyFinale ? ELSIntroTransition::Gameplay : ELSIntroTransition::Travel, FVector::ZeroVector,
				[this, Goal, PlayerController, bEnergyFinale]()
				{
					if (!bEnergyFinale)
					{
						ContinueAfterResults();
						return;
					}
					Goal->PlayEnergyBurst(Cast<ASeedBall>(PlayerController->GetPawn()), [this]() { ContinueAfterResults(); });
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
