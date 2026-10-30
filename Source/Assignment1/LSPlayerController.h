// Last Seed - turns player input into commands for the ball.
//
// Purpose: builds every Enhanced Input action and the mapping context in code at runtime, so no input
// assets are needed. It then forwards input to the possessed ASeedBall. Phase 7 adds widgets and
// game/UI input mode switching.
// Design pattern: command-style forwarding. The controller knows the keys, the ball knows the behaviour.
// Connections: spawned by ALSGameMode. Calls the input functions on ASeedBall and unlocks forms through
// ULSGameInstance for the test commands.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "SeedFormTypes.h"
#include "LSPlayerController.generated.h"

class ASeedBall;
class UInputAction;
class UInputMappingContext;
struct FInputActionInstance;
struct FInputActionValue;

UCLASS()
class ASSIGNMENT1_API ALSPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** Console test command: unlocks Stone and Dandelion. */
	UFUNCTION(Exec)
	void LSUnlockAllForms();

	/** Console test command: kills the ball to test respawning. */
	UFUNCTION(Exec)
	void LSKillBall();

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void OnPossess(APawn* InPawn) override;

	/** Multiplies mouse and gamepad look speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float LookSensitivity = 1.f;

	/** Gamepad look speed at full stick. Legacy input scales multiply it by 2.5 to give degrees/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float GamepadLookRate = 60.f;

	/** Stick values below this are ignored, which stops drift on worn sticks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0", ClampMax = "1"))
	float StickDeadZone = 0.2f;

	/** Starting camera pitch in degrees. Negative looks down at the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float InitialCameraPitch = -20.f;

	/** Lowest camera pitch in degrees (looking down from above). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float MinCameraPitch = -70.f;

	/** Highest camera pitch in degrees (looking up from low down). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float MaxCameraPitch = 30.f;

private:
	void CreateInputObjects();
	void BindInputActions();

	void HandleMove(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleJumpPressed();
	void HandleJumpReleased();
	void HandleSlam();
	void HandleSelectForm(const FInputActionInstance& Instance, ESeedForm Form);
	void HandleCycleForm(const FInputActionValue& Value);
	void HandleTogglePause();

	ASeedBall* GetBall() const;

	// UPROPERTY keeps these runtime-created objects alive: otherwise garbage collection would delete them.
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> GameplayContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SlamAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectSeedAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectStoneAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SelectDandelionAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> CycleFormAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> PauseAction;
};
