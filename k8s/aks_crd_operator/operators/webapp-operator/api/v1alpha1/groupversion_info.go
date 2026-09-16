// Package v1alpha1 contains API Schema definitions for the webapp v1alpha1 API group.
// This file is generated as-is by `kubebuilder create api`; reproduced here so the
// package compiles without re-running the scaffold command.
// +kubebuilder:object:generate=true
// +groupName=webapp.platformlab.dev
package v1alpha1

import (
	"k8s.io/apimachinery/pkg/runtime/schema"
	"sigs.k8s.io/controller-runtime/pkg/scheme"
)

var (
	// GroupVersion is group version used to register these objects.
	GroupVersion = schema.GroupVersion{Group: "webapp.platformlab.dev", Version: "v1alpha1"}

	// SchemeBuilder is used to add go types to the GroupVersionKind scheme.
	SchemeBuilder = &scheme.Builder{GroupVersion: GroupVersion}

	// AddToScheme adds the types in this group-version to the given scheme.
	AddToScheme = SchemeBuilder.AddToScheme
)
