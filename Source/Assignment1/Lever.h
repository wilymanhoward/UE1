// Last Seed - a floor lever thrown by a heavy block pushed up against it.
//
// Purpose: an iron lever on a wooden plinth. Push something heavy (the pushable block) up against the plinth's
// front end and the handle swings over; move it away and the handle swings back. The player's ball never counts, so
// the block has to stay there to hold the lever on.
// Design pattern: observer. Gates subscribe to OnLeverOn and OnLeverOff; the lever doesn't know who is listening.
// Connections: list it in a gate's RequiredLevers. Its meshes (Base, Iron, Cap, Rod, Grip) are set by the level build.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Lever.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnLeverChanged);

UCLASS()
class ASSIGNMENT1_API ALever : public AActor
{
	GENERATED_BODY()

public:
	ALever();

	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintPure, Category = "Lever")
	bool IsOn() const { return bOn; }

	/** Fires when enough weight comes to rest against the lever. */
	UPROPERTY(BlueprintAssignable, Category = "Lever")
	FOnLeverChanged OnLeverOn;

	/** Fires when that weight is taken away. */
	UPROPERTY(BlueprintAssignable, Category = "Lever")
	FOnLeverChanged OnLeverOff;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** The wooden plinth. Solid, so a pushed block stops against its front end. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Base;

	/** The iron rails, arc bracket, gear and axle. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Iron;

	/** The painted band over the arc. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Cap;

	/** The handle turns about this point's Y axis, at the axle. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> ArmPivot;

	/** The iron rod, collars and knob. No collision, so it never knocks the block or the ball. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Rod;

	/** The leather grip on the rod. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Grip;

	/** In front of the plinth's front end (local -X): weight resting here throws the lever. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UBoxComponent> PushZone;

	/** Mass in kg that must rest against the lever. The pushable block is 52. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RequiredMassKg = 40.f;

	/** Handle angle, in degrees about the pivot's Y axis, when off. Positive leans it toward local -X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float OffPitch = 40.f;

	/** Handle angle when on: thrown over, away from the block. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float OnPitch = -40.f;

	/** How fast the handle swings, in degrees per second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float SwingSpeed = 160.f;

private:
	float GetMassAgainst() const;

	bool bOn = false;
	float CurrentPitch = 40.f;
};
