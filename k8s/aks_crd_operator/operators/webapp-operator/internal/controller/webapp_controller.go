/*
Generated scaffold comes from `kubebuilder create api`; the Reconcile logic
below is hand-written for this tutorial.
*/

package controller

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	webappv1alpha1 "platformlab.dev/webapp-operator/api/v1alpha1"
)

// WebAppReconciler reconciles a WebApp object.
type WebAppReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=webapp.platformlab.dev,resources=webapps,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=webapp.platformlab.dev,resources=webapps/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=webapp.platformlab.dev,resources=webapps/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups="",resources=services,verbs=get;list;watch;create;update;patch;delete

// Reconcile drives the actual Deployment+Service toward what the WebApp
// object asks for. It's called whenever a WebApp, or a Deployment/Service it
// owns, changes -- see SetupWithManager below for the watches that trigger it.
func (r *WebAppReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	var webApp webappv1alpha1.WebApp
	if err := r.Get(ctx, req.NamespacedName, &webApp); err != nil {
		// Object gone -- nothing to do. Owned Deployment/Service are removed
		// by Kubernetes garbage collection via the owner references we set
		// below, so there's no cleanup logic (and no finalizer) needed here.
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	if err := r.reconcileDeployment(ctx, &webApp); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconciling deployment: %w", err)
	}

	if err := r.reconcileService(ctx, &webApp); err != nil {
		return ctrl.Result{}, fmt.Errorf("reconciling service: %w", err)
	}

	if err := r.updateStatus(ctx, &webApp); err != nil {
		return ctrl.Result{}, fmt.Errorf("updating status: %w", err)
	}

	logger.Info("reconciled WebApp", "name", webApp.Name, "namespace", webApp.Namespace)
	return ctrl.Result{}, nil
}

func labelsFor(webApp *webappv1alpha1.WebApp) map[string]string {
	return map[string]string{
		"app.kubernetes.io/name":       "webapp",
		"app.kubernetes.io/instance":   webApp.Name,
		"app.kubernetes.io/managed-by": "webapp-operator",
	}
}

func (r *WebAppReconciler) reconcileDeployment(ctx context.Context, webApp *webappv1alpha1.WebApp) error {
	replicas := int32(1)
	if webApp.Spec.Replicas != nil {
		replicas = *webApp.Spec.Replicas
	}
	port := webApp.Spec.Port
	if port == 0 {
		port = 8080
	}
	labels := labelsFor(webApp)

	deployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      webApp.Name,
			Namespace: webApp.Namespace,
		},
	}

	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
		deployment.Labels = labels
		deployment.Spec.Replicas = &replicas
		deployment.Spec.Selector = &metav1.LabelSelector{MatchLabels: labels}
		deployment.Spec.Template = corev1.PodTemplateSpec{
			ObjectMeta: metav1.ObjectMeta{Labels: labels},
			Spec: corev1.PodSpec{
				Containers: []corev1.Container{
					{
						Name:  "webapp",
						Image: webApp.Spec.Image,
						Ports: []corev1.ContainerPort{
							{ContainerPort: port},
						},
					},
				},
			},
		}
		// Ties the Deployment's lifecycle to the WebApp: deleting the WebApp
		// lets Kubernetes garbage-collect this Deployment automatically.
		return controllerutil.SetControllerReference(webApp, deployment, r.Scheme)
	})
	return err
}

func (r *WebAppReconciler) reconcileService(ctx context.Context, webApp *webappv1alpha1.WebApp) error {
	port := webApp.Spec.Port
	if port == 0 {
		port = 8080
	}
	labels := labelsFor(webApp)

	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{
			Name:      webApp.Name,
			Namespace: webApp.Namespace,
		},
	}

	_, err := controllerutil.CreateOrUpdate(ctx, r.Client, service, func() error {
		service.Labels = labels
		service.Spec.Selector = labels
		service.Spec.Ports = []corev1.ServicePort{
			{
				Port:       80,
				TargetPort: intstr.FromInt32(port),
			},
		}
		return controllerutil.SetControllerReference(webApp, service, r.Scheme)
	})
	return err
}

func (r *WebAppReconciler) updateStatus(ctx context.Context, webApp *webappv1alpha1.WebApp) error {
	var deployment appsv1.Deployment
	if err := r.Get(ctx, types.NamespacedName{Name: webApp.Name, Namespace: webApp.Namespace}, &deployment); err != nil {
		if apierrors.IsNotFound(err) {
			return nil
		}
		return err
	}

	webApp.Status.AvailableReplicas = deployment.Status.AvailableReplicas
	return r.Status().Update(ctx, webApp)
}

// SetupWithManager wires the controller into the manager: it watches WebApp
// objects directly, and Owns() the Deployment/Service kinds so an edit or
// deletion of either (e.g. `kubectl delete deploy`) triggers a re-reconcile
// that puts them back -- this is what makes the operator self-healing.
func (r *WebAppReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&webappv1alpha1.WebApp{}).
		Owns(&appsv1.Deployment{}).
		Owns(&corev1.Service{}).
		Complete(r)
}
