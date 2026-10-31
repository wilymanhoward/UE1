// Last Seed - a log balanced on a pivot, which tips under whatever weight is on it.
//
// Purpose: a mass puzzle. Weight further from the pivot turns it harder, so Stone tips it quickly and Seed has to roll
// far along it. A counterweight holds one end down until enough weight passes the pivot, and setting it above what Seed
// can manage makes a log only Stone can tip.
// Design pattern: none. It moves itself each tick instead of using physics simulation, so it can't fling or jam the ball.
// Connections: reads the mass of any simulating body in Trigger, which covers ASeedBall and APushableBlock.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TiltingLog.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ATiltingLog : public AActor
{
	GENERATED_BODY()

public:
	ATiltingLog();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

protected:
	/** Doesn't turn. The actor's location is the pivot. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** Turns around Root's Y axis. Everything on the log is attached to this. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Beam;

	/** The smooth flat surface the ball rolls on. A plain box keeps the bark's bumps from catching it. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UBoxComponent> Deck;

	/** Finds the bodies resting on the log. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UBoxComponent> Trigger;

	/** What the player sees. It has no collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> LogMesh;

	/** Half the log's length in cm, along the actor's X axis. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "100"))
	float HalfLength = 800.f;

	/** Half the log's width in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "60"))
	float HalfWidth = 180.f;

	/** The furthest it tips either way, in degrees. Above about 12, Stone can't roll up it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1", ClampMax = "30"))
	float MaxTiltDegrees = 10.f;

	/** Holds the -X end down. In kg x cm, so Seed (20 kg) at the far end of an 800 cm half gives 16000, and Stone (80 kg) gives 64000. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float CounterweightKgCm = 6000.f;

	/** How quickly a weight difference turns the log, in degrees per second squared per kg x cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float TiltResponse = 0.0015f;

	/** Stops the log swinging forever. Higher settles sooner. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float Damping = 2.5f;

private:
	/** Weight times distance from the pivot, added up for everything on the log. Positive is toward +X. */
	float GetLoadKgCm() const;

	/** Positive raises the +X end. */
	float TiltDegrees = 0.f;
	float TiltSpeed = 0.f;
};
