// See LSPlayerController.h for this class's purpose, pattern and connections.

#include "LSPlayerController.h"

#include "Camera/PlayerCameraManager.h"
#include "Engine/Engine.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "LSGameInstance.h"
#include "LSGameMode.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

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
}

void ALSPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);

	SetControlRotation(FRotator(InitialCameraPitch, InPawn->GetActorRotation().Yaw, 0.f));
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
}

ASeedBall* ALSPlayerController::GetBall() const
{
	return GetPawn<ASeedBall>();
}

void ALSPlayerController::HandleMove(const FInputActionValue& Value)
{
	if (ASeedBall* Ball = GetBall())
	{
		Ball->SetMoveInput(Value.Get<FVector2D>());
	}
}

void ALSPlayerController::HandleLook(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>() * LookSensitivity;
	AddYawInput(Look.X);
	// The project uses legacy input scales, where pitch is multiplied by -2.5.
	// Negating here makes pushing up look up. If legacy scales are ever disabled, remove this minus.
	AddPitchInput(-Look.Y);
}

void ALSPlayerController::HandleJumpPressed()
{
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
	// shortcut: pauses with no menu, Phase 7 replaces this with ULSPauseMenuWidget.
	SetPause(!IsPaused());
}

void ALSPlayerController::ShowPrompt(const FText& Message, float Duration)
{
	// shortcut: debug text, not visible in Shipping builds, Phase 7 sends this to ULSHUDWidget.
	GEngine->AddOnScreenDebugMessage(-1, Duration, FColor::Yellow, Message.ToString());
}

void ALSPlayerController::ShowRestorationStatus()
{
	// shortcut: temporary text, Phase 7 shows this on the HUD and removes this function.
	const URestorationSubsystem* Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	const FString Status = FString::Printf(TEXT("Life Notes %d/%d - Restoration %d%%"),
		Restoration->GetNotesCollected(), Restoration->GetNotesTotal(), FMath::RoundToInt(Restoration->GetRestoration() * 100.f));
	ShowPrompt(FText::FromString(Status), StatusPromptDuration);
}

void ALSPlayerController::LSDrainRestoration(float Amount)
{
	GetWorld()->GetSubsystem<URestorationSubsystem>()->DrainRestoration(Amount);
	ShowRestorationStatus();
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
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->CompleteLevel();
	}
}
