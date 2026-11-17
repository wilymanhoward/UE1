// See LSPlayerController.h for this class's purpose, pattern and connections.

#include "LSPlayerController.h"

#include "Blueprint/UserWidget.h"
#include "Camera/PlayerCameraManager.h"
#include "CheckpointShrine.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "EngineUtils.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "LevelGoal.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "LifeNote.h"
#include "LSGameInstance.h"
#include "LSGameMode.h"
#include "LSHUDWidget.h"
#include "LSMainMenuWidget.h"
#include "LSPauseMenuWidget.h"
#include "LSResultsWidget.h"
#include "LSStoryCardWidget.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"
#include "Sound/SoundClass.h"
#include "Sound/SoundMix.h"

namespace
{
	UInputAction* MakeAction(UObject* Outer, EInputActionValueType ValueType)
	{
		UInputAction* Action = NewObject<UInputAction>(Outer);
		Action->ValueType = ValueType;
		return Action;
	}

	// Flips the sign of the input, for keys such as S and A.
	void AddNegate(FEnhancedActionKeyMapping& Mapping, UObject* Outer)
	{
		Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(Outer));
	}

	// Moves a key's X value into Y. Keys only produce X, and W/S must drive the forward (Y) axis.
	void AddSwapXY(FEnhancedActionKeyMapping& Mapping, UObject* Outer)
	{
		Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Outer));
	}

	void AddDeadZone(FEnhancedActionKeyMapping& Mapping, UObject* Outer, float LowerThreshold)
	{
		UInputModifierDeadZone* DeadZone = NewObject<UInputModifierDeadZone>(Outer);
		DeadZone->LowerThreshold = LowerThreshold;
		Mapping.Modifiers.Add(DeadZone);
	}
}

void ALSPlayerController::BeginPlay()
{
	Super::BeginPlay();

	SetInputMode(FInputModeGameOnly());

	if (PlayerCameraManager)
	{
		PlayerCameraManager->ViewPitchMin = MinCameraPitch;
		PlayerCameraManager->ViewPitchMax = MaxCameraPitch;
	}

	if (VolumeMix)
	{
		UGameplayStatics::PushSoundMixModifier(this, VolumeMix);
	}
	ApplyVolumeSettings();

	const ALSGameMode* GameMode = GetLSGameMode();
	if (GameMode && GameMode->IsMenuLevel())
	{
		if (MainMenuClass)
		{
			OpenMenu(CreateWidget<ULSMainMenuWidget>(this, MainMenuClass));
		}
		else
		{
			UE_LOG(LogTemp, Warning, TEXT("Last Seed: assign Main Menu Class on the player controller."));
		}
	}
	else if (HUDClass)
	{
		HUD = CreateWidget<ULSHUDWidget>(this, HUDClass);
		HUD->AddToViewport();
		if (ASeedBall* Ball = GetBall())
		{
			HUD->SetBall(Ball);
		}
	}
}

void ALSPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);

	SetControlRotation(FRotator(InitialCameraPitch, InPawn->GetActorRotation().Yaw, 0.f));

	// The engine may possess the pawn before or after BeginPlay, so the HUD connects in both places.
	ASeedBall* Ball = Cast<ASeedBall>(InPawn);
	if (HUD && Ball)
	{
		HUD->SetBall(Ball);
	}
}

ALSGameMode* ALSPlayerController::GetLSGameMode() const
{
	return GetWorld()->GetAuthGameMode<ALSGameMode>();
}

void ALSPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();

	CreateInputObjects();
	BindInputActions();

	if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(GameplayContext, 0);
	}
}

void ALSPlayerController::CreateInputObjects()
{
	GameplayContext = NewObject<UInputMappingContext>(this);
	UInputMappingContext* Context = GameplayContext;

	// Move: X = right, Y = forward.
	MoveAction = MakeAction(this, EInputActionValueType::Axis2D);
	AddSwapXY(Context->MapKey(MoveAction, EKeys::W), Context);
	FEnhancedActionKeyMapping& BackKey = Context->MapKey(MoveAction, EKeys::S);
	AddSwapXY(BackKey, Context);
	AddNegate(BackKey, Context);
	AddNegate(Context->MapKey(MoveAction, EKeys::A), Context);
	Context->MapKey(MoveAction, EKeys::D);
	AddDeadZone(Context->MapKey(MoveAction, EKeys::Gamepad_Left2D), Context, StickDeadZone);

	// Look: the mouse reports a distance moved, while a stick reports a held position.
	// The stick is scaled by frame time so its turn speed is the same at any frame rate.
	LookAction = MakeAction(this, EInputActionValueType::Axis2D);
	Context->MapKey(LookAction, EKeys::Mouse2D);
	FEnhancedActionKeyMapping& StickLook = Context->MapKey(LookAction, EKeys::Gamepad_Right2D);
	AddDeadZone(StickLook, Context, StickDeadZone);
	StickLook.Modifiers.Add(NewObject<UInputModifierScaleByDeltaTime>(Context));
	UInputModifierScalar* StickRate = NewObject<UInputModifierScalar>(Context);
	StickRate->Scalar = FVector(GamepadLookRate);
	StickLook.Modifiers.Add(StickRate);

	JumpAction = MakeAction(this, EInputActionValueType::Boolean);
	Context->MapKey(JumpAction, EKeys::SpaceBar);
	Context->MapKey(JumpAction, EKeys::Gamepad_FaceButton_Bottom);

	SlamAction = MakeAction(this, EInputActionValueType::Boolean);
	Context->MapKey(SlamAction, EKeys::LeftControl);
	Context->MapKey(SlamAction, EKeys::LeftMouseButton);
	Context->MapKey(SlamAction, EKeys::Gamepad_FaceButton_Right);

	SelectSeedAction = MakeAction(this, EInputActionValueType::Boolean);
	Context->MapKey(SelectSeedAction, EKeys::One);
	Context->MapKey(SelectSeedAction, EKeys::Gamepad_DPad_Up);

	SelectStoneAction = MakeAction(this, EInputActionValueType::Boolean);
	Context->MapKey(SelectStoneAction, EKeys::Two);
	Context->MapKey(SelectStoneAction, EKeys::Gamepad_DPad_Left);

	SelectDandelionAction = MakeAction(this, EInputActionValueType::Boolean);
	Context->MapKey(SelectDandelionAction, EKeys::Three);
	Context->MapKey(SelectDandelionAction, EKeys::Gamepad_DPad_Right);

	// Cycle: a single axis where the sign gives the direction.
	CycleFormAction = MakeAction(this, EInputActionValueType::Axis1D);
	AddNegate(Context->MapKey(CycleFormAction, EKeys::Q), Context);
	Context->MapKey(CycleFormAction, EKeys::E);
	AddNegate(Context->MapKey(CycleFormAction, EKeys::Gamepad_LeftShoulder), Context);
	Context->MapKey(CycleFormAction, EKeys::Gamepad_RightShoulder);

	PauseAction = MakeAction(this, EInputActionValueType::Boolean);
	// Without this flag, the key that pauses the game could never unpause it.
	PauseAction->bTriggerWhenPaused = true;
	Context->MapKey(PauseAction, EKeys::Escape);
	Context->MapKey(PauseAction, EKeys::Gamepad_Special_Right);

	if (bEnableDevCheats)
	{
		DevUnlockFormsAction = MakeAction(this, EInputActionValueType::Boolean);
		Context->MapKey(DevUnlockFormsAction, EKeys::F1);

		DevNextCheckpointAction = MakeAction(this, EInputActionValueType::Boolean);
		Context->MapKey(DevNextCheckpointAction, EKeys::F2);

		DevCollectNotesAction = MakeAction(this, EInputActionValueType::Boolean);
		Context->MapKey(DevCollectNotesAction, EKeys::F3);
	}
}

void ALSPlayerController::BindInputActions()
{
	UEnhancedInputComponent* Input = CastChecked<UEnhancedInputComponent>(InputComponent);

	// Triggered fires every frame while held. Completed fires once on release with a zero value,
	// which is what stops the ball receiving the last held direction forever.
	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ALSPlayerController::HandleMove);
	Input->BindAction(MoveAction, ETriggerEvent::Completed, this, &ALSPlayerController::HandleMove);
	Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &ALSPlayerController::HandleLook);
	Input->BindAction(JumpAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleJumpPressed);
	Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &ALSPlayerController::HandleJumpReleased);
	Input->BindAction(SlamAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleSlam);
	Input->BindAction(SelectSeedAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleSelectForm, ESeedForm::Seed);
	Input->BindAction(SelectStoneAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleSelectForm, ESeedForm::Stone);
	Input->BindAction(SelectDandelionAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleSelectForm, ESeedForm::Dandelion);
	Input->BindAction(CycleFormAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleCycleForm);
	Input->BindAction(PauseAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleTogglePause);

	if (bEnableDevCheats)
	{
		Input->BindAction(DevUnlockFormsAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleDevUnlockForms);
		Input->BindAction(DevNextCheckpointAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleDevNextCheckpoint);
		Input->BindAction(DevCollectNotesAction, ETriggerEvent::Started, this, &ALSPlayerController::HandleDevCollectNotes);
	}
}

ASeedBall* ALSPlayerController::GetBall() const
{
	return GetPawn<ASeedBall>();
}

void ALSPlayerController::HandleMove(const FInputActionValue& Value)
{
	if (OpeningTutorialStep == 1 && !Value.Get<FVector2D>().IsNearlyZero())
	{
		TutorialInputTime += GetWorld()->GetDeltaSeconds();
		if (TutorialInputTime >= 0.7f) AdvanceOpeningTutorial();
	}
	if (ASeedBall* Ball = GetBall())
	{
		Ball->SetMoveInput(Value.Get<FVector2D>());
	}
}

void ALSPlayerController::HandleLook(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>() * LookSensitivity;
	if (OpeningTutorialStep == 2 && !Look.IsNearlyZero())
	{
		TutorialInputTime += GetWorld()->GetDeltaSeconds();
		if (TutorialInputTime >= 0.35f) AdvanceOpeningTutorial();
	}
	AddYawInput(Look.X);
	// The project uses legacy input scales, where pitch is multiplied by -2.5.
	// Negating here makes pushing up look up. If legacy scales are ever disabled, remove this minus.
	AddPitchInput(-Look.Y);
}

void ALSPlayerController::HandleJumpPressed()
{
	if (OpeningTutorialStep == 3) AdvanceOpeningTutorial();
	if (ASeedBall* Ball = GetBall())
	{
		Ball->JumpPressed();
	}
}

void ALSPlayerController::HandleJumpReleased()
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->JumpReleased();
	}
}

void ALSPlayerController::HandleSlam()
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->SlamPressed();
	}
}

void ALSPlayerController::HandleSelectForm(const FInputActionInstance& Instance, ESeedForm Form)
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->TrySwitchForm(Form);
	}
}

void ALSPlayerController::HandleCycleForm(const FInputActionValue& Value)
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->CycleForm(Value.Get<float>() > 0.f ? 1 : -1);
	}
}

void ALSPlayerController::HandleTogglePause()
{
	// This key can close the pause menu, but must not close results or story cards, which have their own buttons.
	if (ActiveMenu)
	{
		if (ActiveMenu->IsA<ULSPauseMenuWidget>())
		{
			CloseMenu();
		}
		return;
	}

	if (bStoryPlaying)
	{
		return;
	}

	if (PauseMenuClass)
	{
		OpenMenu(CreateWidget<ULSPauseMenuWidget>(this, PauseMenuClass));
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("Last Seed: assign Pause Menu Class on the player controller."));
	}
}

void ALSPlayerController::HandleDevUnlockForms()
{
	LSUnlockAllForms();
	ShowPrompt(FText::FromString(TEXT("Dev: all forms unlocked")), 2.f);
}

void ALSPlayerController::HandleDevNextCheckpoint()
{
	ASeedBall* Ball = GetBall();
	if (!Ball)
	{
		return;
	}

	// The nearest shrine not reached yet is normally the next one along the path.
	const ACheckpointShrine* Nearest = nullptr;
	double NearestDistance = TNumericLimits<double>::Max();
	for (TActorIterator<ACheckpointShrine> It(GetWorld()); It; ++It)
	{
		const double Distance = FVector::DistSquared(It->GetActorLocation(), Ball->GetActorLocation());
		if (!It->IsActivated() && Distance < NearestDistance)
		{
			Nearest = *It;
			NearestDistance = Distance;
		}
	}

	if (Nearest)
	{
		// Slightly above, so the ball drops onto the ground and doesn't start inside it.
		Ball->TeleportBall(Nearest->GetActorLocation() + FVector(0.f, 0.f, 100.f));
	}
	else
	{
		ShowPrompt(FText::FromString(TEXT("Dev: no checkpoints left")), 2.f);
	}
}

void ALSPlayerController::HandleDevCollectNotes()
{
	ASeedBall* Ball = GetBall();
	if (!Ball)
	{
		return;
	}

	// Real notes are collected, so the count, restoration and stars all stay correct.
	int32 Remaining = 5;
	for (TActorIterator<ALifeNote> It(GetWorld()); It && Remaining > 0; ++It, --Remaining)
	{
		It->OnBallOverlap(Ball);
	}
}

void ALSPlayerController::OpenMenu(UUserWidget* Menu)
{
	ActiveMenu = Menu;
	// Above the HUD, which uses the default order of 0.
	Menu->AddToViewport(1);
	SetHUDVisible(false);

	// Game and UI, not UI only, because UI only would block the Pause key that closes the pause menu.
	FInputModeGameAndUI InputMode;
	InputMode.SetHideCursorDuringCapture(false);
	SetInputMode(InputMode);
	bShowMouseCursor = true;

	// Stops the ball, blobs, storm and timer. Widgets still work while the game is paused.
	SetPause(true);
}

void ALSPlayerController::CloseMenu()
{
	if (ActiveMenu)
	{
		ActiveMenu->RemoveFromParent();
		ActiveMenu = nullptr;
	}

	SetHUDVisible(true);
	SetInputMode(FInputModeGameOnly());
	bShowMouseCursor = false;
	SetPause(false);
}

void ALSPlayerController::SetHUDVisible(bool bVisible)
{
	if (HUD)
	{
		// The HUD only displays information, so it should never catch mouse clicks.
		HUD->SetVisibility(bVisible ? ESlateVisibility::SelfHitTestInvisible : ESlateVisibility::Collapsed);
	}
}

void ALSPlayerController::SetGameplayInputEnabled(bool bEnabled)
{
	UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer());
	if (Subsystem)
	{
		if (bEnabled)
		{
			Subsystem->AddMappingContext(GameplayContext, 0);
		}
		else
		{
			Subsystem->RemoveMappingContext(GameplayContext);
		}
	}

	if (ASeedBall* Ball = GetBall(); Ball && !bEnabled)
	{
		// The key's release may never arrive while the context is removed, so the ball would keep the last direction.
		Ball->SetMoveInput(FVector2D::ZeroVector);
		Ball->JumpReleased();
	}
}

void ALSPlayerController::PlayStory(ULevelSequence* Sequence, const TArray<FText>& Cards, TFunction<void()> OnFinished)
{
	BeginStory(MoveTemp(OnFinished));

	if (Sequence)
	{
		ALevelSequenceActor* SequenceActor = nullptr;
		ULevelSequencePlayer* SequencePlayer = ULevelSequencePlayer::CreateLevelSequencePlayer(this, Sequence, FMovieSceneSequencePlaybackSettings(), SequenceActor);
		if (SequencePlayer)
		{
			StorySequenceActor = SequenceActor;
			SequencePlayer->OnFinished.AddDynamic(this, &ALSPlayerController::HandleSequenceFinished);
			SequencePlayer->Play();
			return;
		}
	}
	else if (!Cards.IsEmpty() && StoryCardClass)
	{
		ULSStoryCardWidget* CardWidget = CreateWidget<ULSStoryCardWidget>(this, StoryCardClass);
		CardWidget->ShowCards(Cards);
		CardWidget->OnFinished.AddDynamic(this, &ALSPlayerController::HandleStoryCardsFinished);
		OpenMenu(CardWidget);
		return;
	}

	// Nothing could be played, so carry on straight away.
	FinishStory();
}

void ALSPlayerController::BeginStory(TFunction<void()> OnFinished)
{
	// A new story replaces one still playing, such as the ball reaching the goal during a cutscene.
	if (bStoryPlaying)
	{
		FinishStory();
	}

	AfterStory = MoveTemp(OnFinished);
	bStoryPlaying = true;
	SetGameplayInputEnabled(false);
	SetHUDVisible(false);
	if (ALSGameMode* GameMode = GetLSGameMode())
	{
		// A cutscene can't play while paused, so the timer is stopped separately.
		GameMode->SetTimerRunning(false);
	}
}

void ALSPlayerController::PlayIntro(const TArray<FLSIntroShot>& Shots, USoundBase* Music, USoundBase* VoiceOver)
{
	BeginStory(nullptr);
	bOpeningIntro = true;
	ULSIntroWidget* Intro = CreateWidget<ULSIntroWidget>(this, ULSIntroWidget::StaticClass());
	Intro->SetIntro(Shots, Music, VoiceOver);
	// It ends the same way the story cards do: close it, then hand back control.
	Intro->OnFinished.AddDynamic(this, &ALSPlayerController::HandleStoryCardsFinished);
	OpenMenu(Intro);
}

void ALSPlayerController::HandleStoryCardsFinished()
{
	const bool bStartTutorial = bOpeningIntro;
	bOpeningIntro = false;
	CloseMenu();
	FinishStory();
	if (bStartTutorial) AdvanceOpeningTutorial();
}

void ALSPlayerController::AdvanceOpeningTutorial()
{
	++OpeningTutorialStep;
	TutorialInputTime = 0.f;
	if (!HUD) { OpeningTutorialStep = 0; return; }
	switch (OpeningTutorialStep)
	{
	case 1:
		HUD->ShowHint(FText::FromString(TEXT("FIRST STEPS   /   1 OF 3")), FText::FromString(TEXT("W A S D  /  LEFT STICK")),
			NSLOCTEXT("LastSeed", "LearnRoll", "Roll along the forest path."), 0.f);
		break;
	case 2:
		HUD->ShowHint(FText::FromString(TEXT("LOOK AROUND   /   2 OF 3")), FText::FromString(TEXT("MOUSE  /  RIGHT STICK")),
			NSLOCTEXT("LastSeed", "LearnLook", "Move the camera to explore your surroundings."), 0.f);
		break;
	case 3:
		HUD->ShowHint(FText::FromString(TEXT("A LITTLE LEAP   /   3 OF 3")), FText::FromString(TEXT("SPACE  /  A")),
			NSLOCTEXT("LastSeed", "LearnJump", "Jump to clear roots and small obstacles."), 0.f);
		break;
	default:
		OpeningTutorialStep = 0;
		HUD->ShowHint(NSLOCTEXT("LastSeed", "BeginJourney", "YOUR JOURNEY BEGINS"), FText::FromString(TEXT("ESC  /  START   ·   PAUSE")),
			NSLOCTEXT("LastSeed", "SeekNotes", "Follow the path. Collect Life Notes to bring the forest back to life."), 7.f);
		break;
	}
}

void ALSPlayerController::ShowFormUnlock(ESeedForm Form, const FText& Message, float Duration)
{
	OpeningTutorialStep = 0;
	if (HUD)
	{
		const bool bStone = Form == ESeedForm::Stone;
		HUD->ShowHint(FText::FromString(bStone ? TEXT("NEW FORM   /   STONE SHELL") : TEXT("NEW FORM   /   DANDELION")),
			FText::FromString(bStone ? TEXT("2 / D-PAD LEFT    ·    Q E / LB RB TO CYCLE") : TEXT("3 / D-PAD RIGHT    ·    Q E / LB RB TO CYCLE")),
			Message, FMath::Max(Duration, 12.f));
	}
}

void ALSPlayerController::HandleSequenceFinished()
{
	FinishStory();
}

void ALSPlayerController::FinishStory()
{
	bStoryPlaying = false;

	if (StorySequenceActor)
	{
		StorySequenceActor->Destroy();
		StorySequenceActor = nullptr;
	}

	SetGameplayInputEnabled(true);
	SetHUDVisible(true);
	if (ALSGameMode* GameMode = GetLSGameMode())
	{
		GameMode->SetTimerRunning(true);
	}

	// Moved out first, because the callback may start another story, which sets AfterStory again.
	const TFunction<void()> Callback = MoveTemp(AfterStory);
	AfterStory = nullptr;
	if (Callback)
	{
		Callback();
	}
}

void ALSPlayerController::ShowResults(const FLSLevelResult& Result)
{
	if (ResultsClass)
	{
		ULSResultsWidget* Results = CreateWidget<ULSResultsWidget>(this, ResultsClass);
		Results->ShowResult(Result);
		OpenMenu(Results);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("Last Seed: assign Results Class on the player controller. Stars: %d"), Result.Stars);
	}
}

void ALSPlayerController::RestartFromCheckpoint()
{
	CloseMenu();
	if (ASeedBall* Ball = GetBall())
	{
		Ball->Die();
	}
}

void ALSPlayerController::ReturnToMainMenu()
{
	if (MainMenuLevel.IsNull())
	{
		UE_LOG(LogTemp, Warning, TEXT("Last Seed: assign Main Menu Level on the player controller."));
		return;
	}
	UGameplayStatics::OpenLevelBySoftObjectPtr(this, MainMenuLevel);
}

void ALSPlayerController::ApplyVolumeSettings()
{
	const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>();
	if (!GameInstance || !VolumeMix)
	{
		return;
	}

	// A fade time of 0 makes a slider take effect at once. Child classes follow their parent.
	if (MusicClass)
	{
		UGameplayStatics::SetSoundMixClassOverride(this, VolumeMix, MusicClass, GameInstance->GetMusicVolume(), 1.f, 0.f, true);
	}
	if (SfxClass)
	{
		UGameplayStatics::SetSoundMixClassOverride(this, VolumeMix, SfxClass, GameInstance->GetSfxVolume(), 1.f, 0.f, true);
	}
}

void ALSPlayerController::ShowPrompt(const FText& Message, float Duration)
{
	if (OpeningTutorialStep != 0) return;
	if (HUD)
	{
		HUD->ShowPrompt(Message, Duration);
	}
	else
	{
		// shortcut: debug text until WBP_HUD is assigned, not visible in Shipping builds.
		GEngine->AddOnScreenDebugMessage(-1, Duration, FColor::Yellow, Message.ToString());
	}
}

void ALSPlayerController::LSDrainRestoration(float Amount)
{
	GetWorld()->GetSubsystem<URestorationSubsystem>()->DrainRestoration(Amount);
}

void ALSPlayerController::LSDeleteSave()
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->DeleteProgress();
	}
}

void ALSPlayerController::LSUnlockAllForms()
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->UnlockAllForms();
	}
}

void ALSPlayerController::LSKillBall()
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->Die();
	}
}

void ALSPlayerController::LSCompleteLevel()
{
	ALSGameMode* GameMode = GetLSGameMode();
	TActorIterator<ALevelGoal> Goal(GetWorld());
	if (GameMode && Goal)
	{
		GameMode->CompleteLevel(*Goal);
	}
	else
	{
		ShowPrompt(FText::FromString(TEXT("LSCompleteLevel needs a LevelGoal in the level.")), 5.f);
	}
}
